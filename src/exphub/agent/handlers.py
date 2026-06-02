"""Pre-agent command handlers for CrystalPilot.

Each handler inspects the user's message and returns a reply string if it
can handle the request deterministically (no LLM call needed), or ``None``
to fall through to the next handler and ultimately to the LangGraph agent.

The handler chain is evaluated in ``HANDLERS`` order by ``run_handlers()``.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from ..core.beamline import TabKey
from .constants import TAB_MAP, TAB_NAMES, get_experiment_presets
from .workflow import PhaseManager

# Type alias for handler functions
HandlerFn = Callable[
    [str, "Callable[[], dict] | None", "dict[str, dict]", "Callable[[TabKey | int], None] | None"],
    "str | None",
]


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())


# ---------------------------------------------------------------------------
# Individual handlers
# ---------------------------------------------------------------------------

def handle_show_config(
    user_text: str,
    snapshot_fn: Callable[[], dict] | None,
    schema_props: dict[str, dict],
    nav_fn: Callable[[TabKey | int], None] | None,
) -> str | None:
    """Handle "show config" / "current settings" requests."""
    norm = _normalize(user_text)
    triggers = ("show config", "current config", "current settings", "show settings",
                "show parameters", "current parameters", "show current")
    if not any(t in norm for t in triggers):
        return None
    if snapshot_fn is None:
        return "Configuration snapshot is not available."
    snap = snapshot_fn()
    # Filter to only fields that exist in schema (skip internal/list fields)
    config = {k: v for k, v in snap.items() if k in schema_props and v is not None
              and not isinstance(v, list)}
    if not config:
        return "No configuration values are currently set."
    lines = [f"- **{schema_props.get(k, {}).get('title', k)}**: `{v}`"
             for k, v in sorted(config.items())]
    return "**Current Configuration:**\n" + "\n".join(lines)


def handle_list_presets(
    user_text: str,
    snapshot_fn: Callable[[], dict] | None,
    schema_props: dict[str, dict],
    nav_fn: Callable[[TabKey | int], None] | None,
) -> str | None:
    """Handle "list presets" / "what presets" requests."""
    norm = _normalize(user_text)
    if not any(t in norm for t in ("list preset", "show preset", "what preset",
                                    "available preset")):
        return None
    presets = get_experiment_presets()
    if not presets:
        return "No presets are currently registered."
    lines = []
    for name, params in presets.items():
        fields = ", ".join(f"`{k}`=`{v}`" for k, v in params.items())
        lines.append(f"- **{name}**: {fields}")
    example = next(iter(presets))
    return "**Available Presets:**\n" + "\n".join(lines) + \
           f"\n\nUse `apply_preset` or say e.g. *apply {example}* to apply one."


def handle_navigate(
    user_text: str,
    snapshot_fn: Callable[[], dict] | None,
    schema_props: dict[str, dict],
    nav_fn: Callable[[TabKey | int], None] | None,
) -> str | None:
    """Handle "go to [tab]" / "switch to [tab]" requests."""
    if nav_fn is None:
        return None
    norm = _normalize(user_text)
    # Match patterns like "go to ipts info", "switch to data analysis", "open live data"
    m = re.match(r"(?:go to|switch to|open|navigate to|show)\s+(.+)", norm)
    if not m:
        return None
    tab_text = m.group(1).strip().replace("-", "_").replace(" ", "_")
    tab_number = TAB_MAP.get(tab_text)
    if tab_number is None:
        return None  # fall through to agent — might be a more complex request
    nav_fn(tab_number)
    return f"Switched to **{TAB_NAMES.get(tab_number, f'tab {tab_number}')}** tab."


def handle_help(
    user_text: str,
    snapshot_fn: Callable[[], dict] | None,
    schema_props: dict[str, dict],
    nav_fn: Callable[[TabKey | int], None] | None,
) -> str | None:
    """Handle "help" / "what can you do" requests."""
    norm = _normalize(user_text)
    if norm not in ("help", "what can you do", "what can you do?",
                    "commands", "capabilities"):
        return None
    presets = get_experiment_presets()
    if presets:
        preset_names = list(presets.keys())
        if len(preset_names) == 1:
            preset_hint = f"say *apply {preset_names[0]}*"
        else:
            preset_hint = f"say *apply {preset_names[0]}* (or {', '.join(preset_names[1:])})"
    else:
        preset_hint = "no presets currently registered"
    return (
        "**CrystalPilot Assistant** can help you with:\n\n"
        "- **Set parameters**: tell me a value and I'll configure it\n"
        "- **Explain parameters**: ask what any field means\n"
        f"- **Apply presets**: {preset_hint}\n"
        "- **Angle plan**: add, edit, or delete runs\n"
        "- **Navigate tabs**: say *go to live data* or *switch to ipts info*\n"
        "- **Show config**: see current settings\n"
        "- **Ask questions**: crystallography, instruments, troubleshooting\n\n"
        "Just type naturally — I'll figure out what you need!"
    )


# ---------------------------------------------------------------------------
# Intent detection (4A)
# ---------------------------------------------------------------------------

_INTENT_START = (
    "start experiment", "new experiment", "begin experiment",
    "start setup", "begin setup", "set up experiment",
    "let's start", "lets start", "let's begin", "lets begin",
)

_INTENT_PHASE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "setup": ("setup", "configure", "ipts info", "sample info", "enter metadata"),
    "monitor": ("monitor", "live data", "live reduction", "stream", "auto update"),
    "plan": ("plan", "angle plan", "strategy", "experiment steering"),
    "refine_plan": ("refine plan", "edit plan", "modify plan", "edit angle"),
    "submit": ("submit", "eic", "execute plan"),
    "observe": ("observe", "instrument status", "motor position", "watch"),
    "analyse": ("analyse", "analyze", "reduction", "integrate", "data analysis"),
}


def handle_intent(
    user_text: str,
    snapshot_fn: Callable[[], dict] | None,
    schema_props: dict[str, dict],
    nav_fn: Callable[[TabKey | int], None] | None,
    *,
    phase_manager: PhaseManager | None = None,
) -> str | None:
    """Detect workflow-starting intents and enter the appropriate phase."""
    if phase_manager is None:
        return None
    norm = _normalize(user_text)

    # "start experiment" → enter phase 0 (setup)
    if any(t in norm for t in _INTENT_START):
        msg = phase_manager.go_to_phase("setup")
        if nav_fn:
            nav_fn(phase_manager.current.tab)
        return msg or "Starting experiment setup."

    # Phase-specific keywords
    for phase_name, keywords in _INTENT_PHASE_KEYWORDS.items():
        if any(kw in norm for kw in keywords):
            msg = phase_manager.go_to_phase(phase_name)
            if msg and nav_fn:
                nav_fn(phase_manager.current.tab)
            return msg

    return None


# ---------------------------------------------------------------------------
# Phase confirmation (4B)
# ---------------------------------------------------------------------------

_CONFIRM_YES = ("yes", "y", "ok", "sure", "proceed", "continue", "next", "go ahead", "ready")
_CONFIRM_NO = ("no", "n", "not yet", "wait", "hold", "stay")


def handle_phase_confirm(
    user_text: str,
    snapshot_fn: Callable[[], dict] | None,
    schema_props: dict[str, dict],
    nav_fn: Callable[[TabKey | int], None] | None,
    *,
    phase_manager: PhaseManager | None = None,
) -> str | None:
    """Handle yes/no confirmation for phase transitions."""
    if phase_manager is None or not phase_manager.is_pending_confirm:
        return None
    norm = _normalize(user_text)

    if norm in _CONFIRM_YES or any(norm.startswith(c) for c in _CONFIRM_YES):
        msg = phase_manager.advance()
        if nav_fn:
            nav_fn(phase_manager.current.tab)
        return msg

    if norm in _CONFIRM_NO or any(norm.startswith(c) for c in _CONFIRM_NO):
        phase_manager.current_state.pending_confirm = False
        return f"Staying in **{phase_manager.current.label}**. Let me know when you're ready to move on."

    return None


# ---------------------------------------------------------------------------
# Workflow status
# ---------------------------------------------------------------------------

def handle_workflow_status(
    user_text: str,
    snapshot_fn: Callable[[], dict] | None,
    schema_props: dict[str, dict],
    nav_fn: Callable[[TabKey | int], None] | None,
    *,
    phase_manager: PhaseManager | None = None,
) -> str | None:
    """Handle 'show status' / 'where am I' requests."""
    if phase_manager is None:
        return None
    norm = _normalize(user_text)
    triggers = ("show status", "workflow status", "where am i", "which phase", "current phase")
    if not any(t in norm for t in triggers):
        return None
    return "**Experiment Workflow:**\n\n" + phase_manager.status_summary()


# ---------------------------------------------------------------------------
# Handler chain
# ---------------------------------------------------------------------------

HANDLERS: list[HandlerFn] = [
    handle_help,
    handle_show_config,
    handle_list_presets,
    handle_navigate,
]

# Handlers that need a PhaseManager are kept separate so run_handlers
# can pass the extra keyword argument without changing the base type.
_PHASE_HANDLERS = [
    handle_phase_confirm,
    handle_intent,
    handle_workflow_status,
]


def run_handlers(
    user_text: str,
    snapshot_fn: Callable[[], dict] | None = None,
    schema_props: dict[str, dict] | None = None,
    nav_fn: Callable[[TabKey | int], None] | None = None,
    phase_manager: PhaseManager | None = None,
) -> str | None:
    """Run through the handler chain, returning the first non-None reply.

    Returns ``None`` if no handler matched — caller should invoke the agent.
    """
    props = schema_props or {}

    # Phase-aware handlers first (confirmation should intercept before anything else)
    if phase_manager is not None:
        for handler in _PHASE_HANDLERS:
            result = handler(user_text, snapshot_fn, props, nav_fn, phase_manager=phase_manager)
            if result is not None:
                return result

    for handler in HANDLERS:
        result = handler(user_text, snapshot_fn, props, nav_fn)
        if result is not None:
            return result
    return None
