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

from .constants import EXPERIMENT_PRESETS, TAB_MAP, TAB_NAMES

# Type alias for handler functions
HandlerFn = Callable[
    [str, "Callable[[], dict] | None", "dict[str, dict]", "Callable[[int], None] | None"],
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
    nav_fn: Callable[[int], None] | None,
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
    nav_fn: Callable[[int], None] | None,
) -> str | None:
    """Handle "list presets" / "what presets" requests."""
    norm = _normalize(user_text)
    if not any(t in norm for t in ("list preset", "show preset", "what preset",
                                    "available preset")):
        return None
    lines = []
    for name, params in EXPERIMENT_PRESETS.items():
        fields = ", ".join(f"`{k}`=`{v}`" for k, v in params.items())
        lines.append(f"- **{name}**: {fields}")
    return "**Available Presets:**\n" + "\n".join(lines) + \
           "\n\nUse `apply_preset` or say e.g. *apply topaz_standard* to apply one."


def handle_navigate(
    user_text: str,
    snapshot_fn: Callable[[], dict] | None,
    schema_props: dict[str, dict],
    nav_fn: Callable[[int], None] | None,
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
    nav_fn: Callable[[int], None] | None,
) -> str | None:
    """Handle "help" / "what can you do" requests."""
    norm = _normalize(user_text)
    if norm not in ("help", "what can you do", "what can you do?",
                    "commands", "capabilities"):
        return None
    return (
        "**CrystalPilot Assistant** can help you with:\n\n"
        "- **Set parameters**: tell me a value and I'll configure it\n"
        "- **Explain parameters**: ask what any field means\n"
        "- **Apply presets**: say *apply topaz_standard* (or corelli/mandi)\n"
        "- **Angle plan**: add, edit, or delete runs\n"
        "- **Navigate tabs**: say *go to live data* or *switch to ipts info*\n"
        "- **Show config**: see current settings\n"
        "- **Ask questions**: crystallography, instruments, troubleshooting\n\n"
        "Just type naturally — I'll figure out what you need!"
    )


# ---------------------------------------------------------------------------
# Handler chain
# ---------------------------------------------------------------------------

HANDLERS: list[HandlerFn] = [
    handle_help,
    handle_show_config,
    handle_list_presets,
    handle_navigate,
]


def run_handlers(
    user_text: str,
    snapshot_fn: Callable[[], dict] | None = None,
    schema_props: dict[str, dict] | None = None,
    nav_fn: Callable[[int], None] | None = None,
) -> str | None:
    """Run through the handler chain, returning the first non-None reply.

    Returns ``None`` if no handler matched — caller should invoke the agent.
    """
    props = schema_props or {}
    for handler in HANDLERS:
        result = handler(user_text, snapshot_fn, props, nav_fn)
        if result is not None:
            return result
    return None
