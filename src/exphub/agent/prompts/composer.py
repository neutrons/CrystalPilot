"""Assemble the agent's system prompt from layered fragments.

Layout::

    [Core identity]              prompts/core_identity.md   (beamline-agnostic, always)
    [Technique context]          techniques/<id>/prompts/context.md  (per active technique)
    [Beamline context]           <beamline_pkg>/<context_prompt>  (per active spec)
    [Task instructions]          prompts/tasks/<task>.md   (per active task; optional)

If a fragment is missing the composer skips it silently and falls back to the
legacy single-file ``prompts/system_prompt.md`` if no fragments exist at all.
This keeps existing deployments working while letting new code opt into the
composable layout.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from ...core.beamline import get_technique
from ..core_aliases import active_spec  # safe lazy aliases; see file

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).parent
_LEGACY_PROMPT = _PROMPT_DIR / "system_prompt.md"
_CORE_IDENTITY = _PROMPT_DIR / "core_identity.md"
_TASKS_DIR = _PROMPT_DIR / "tasks"

_SEPARATOR = "\n\n---\n\n"


def _read(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _technique_context_prompt(beamline_id: str | None) -> str:
    """Resolve the active beamline's *technique* context fragment, if any.

    The technique layer (e.g. "single-crystal diffraction") sits between the
    beamline-agnostic core identity and the per-beamline context, so the LLM
    gets technique-level concepts that every beamline of the family shares.
    """
    try:
        spec = active_spec(beamline_id)
        manifest = get_technique(spec.technique)
    except Exception:
        return ""
    if manifest.prompts_dir is None:
        return ""
    return _read(manifest.prompts_dir / "context.md")


def _beamline_context_prompt(beamline_id: str | None) -> str:
    """Resolve the active beamline's context fragment, if any."""
    try:
        spec = active_spec(beamline_id)
    except Exception:
        return ""
    ctx_prompt = spec.agent.context_prompt
    if ctx_prompt is None:
        return ""
    return _read(spec.resolve(ctx_prompt))


def _task_prompt(task: str | None) -> str:
    if not task:
        return ""
    return _read(_TASKS_DIR / f"{task}.md")


def compose_system_prompt(
    beamline_id: str | None = None,
    task: str | None = None,
) -> str:
    """Return the assembled prompt; falls back to ``system_prompt.md`` if no fragments exist."""
    parts: list[str] = []
    for piece in _layered_pieces(beamline_id=beamline_id, task=task):
        if piece:
            parts.append(piece)
    if parts:
        return _SEPARATOR.join(parts)
    legacy = _read(_LEGACY_PROMPT)
    if legacy:
        return legacy
    return "You are an AI helper for neutron-diffraction experiments. Be concise and helpful."


def _layered_pieces(beamline_id: str | None, task: str | None) -> Iterable[str]:
    yield _read(_CORE_IDENTITY)
    yield _technique_context_prompt(beamline_id)
    yield _beamline_context_prompt(beamline_id)
    yield _task_prompt(task)


def describe_active_context(beamline_id: str | None = None, task: str | None = None) -> str:
    """A single line summarising the active beamline + task.

    For per-turn logging and to inject into the LLM's first SystemMessage.
    """
    try:
        spec = active_spec(beamline_id)
        location = spec.facility + (f"/{spec.target_station}" if spec.target_station else "")
        bl_label = f"{spec.display_name} [{location}]"
    except Exception:
        bl_label = beamline_id or "<unknown>"
    return f"ACTIVE_BEAMLINE: {bl_label} | ACTIVE_TASK: {task or 'experiment_steering'}"
