"""Lightweight experiment-phase state machine for CrystalPilot.

Tracks which phase of the experiment the user is in, scopes schema fields per
phase, and provides confirmation gates between phases.

The phase *sequence* is supplied by the active technique (see
``TechniqueManifest.phases``); this module owns only the state machine. The
single-crystal phase list lives in
``exphub.techniques.single_crystal.agent.phases``.

Inspired by NeuDiff-Agent's PhaseManager but adapted to CrystalPilot's
tab-based navigation.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from ..core.beamline import PhaseDefinition, active_technique

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase state (runtime, per-phase)
# ---------------------------------------------------------------------------


@dataclass
class PhaseState:
    """Runtime state for a single phase."""

    status: str = "pending"  # pending | active | complete
    pending_confirm: bool = False  # waiting for user to confirm advancing


# ---------------------------------------------------------------------------
# PhaseManager
# ---------------------------------------------------------------------------


class PhaseManager:
    """Tracks the current experiment phase and manages transitions.

    The manager enforces a linear phase sequence with confirmation gates: a
    phase must be explicitly completed before advancing to the next. The
    sequence comes from the active technique's manifest unless an explicit
    ``phases`` list is supplied (mainly for tests).
    """

    def __init__(self, phases: Sequence[PhaseDefinition] | None = None) -> None:
        if phases is None:
            phases = active_technique().phases
        self._phases: tuple[PhaseDefinition, ...] = tuple(phases)
        self._phase_names: list[str] = [p.name for p in self._phases]
        self._phase_map: dict[str, PhaseDefinition] = {p.name: p for p in self._phases}
        self._current_idx: int = 0
        self._states: dict[str, PhaseState] = {name: PhaseState() for name in self._phase_names}
        if self._phase_names:
            self._states[self._phase_names[0]].status = "active"

    # ---- Properties ----

    @property
    def phases(self) -> tuple[PhaseDefinition, ...]:
        return self._phases

    @property
    def phase_names(self) -> list[str]:
        return list(self._phase_names)

    @property
    def current(self) -> PhaseDefinition:
        """Return the definition of the current phase."""
        return self._phases[self._current_idx]

    @property
    def current_name(self) -> str:
        return self._phases[self._current_idx].name

    @property
    def current_state(self) -> PhaseState:
        return self._states[self.current_name]

    @property
    def is_pending_confirm(self) -> bool:
        """True if the current phase is waiting for user confirmation to advance."""
        return self.current_state.pending_confirm

    # ---- Phase transitions ----

    def complete_current(self) -> str | None:
        """Mark the current phase as complete and offer to advance.

        Returns a guidance message, or None if already at the last phase.
        """
        self.current_state.status = "complete"
        if self._current_idx + 1 >= len(self._phases):
            return None  # all phases done
        self.current_state.pending_confirm = True
        next_phase = self._phases[self._current_idx + 1]
        return (
            f"**{self.current.label}** phase complete. "
            f"Ready to move to **{next_phase.label}** ({next_phase.description})? "
            f"Say **yes** to continue."
        )

    def advance(self) -> str:
        """Advance to the next phase (call after user confirms).

        Returns a guidance message about the new phase.
        """
        self.current_state.pending_confirm = False
        if self._current_idx + 1 >= len(self._phases):
            return "All experiment phases are complete."
        self._current_idx += 1
        self.current_state.status = "active"
        phase = self.current
        return f"Now in **{phase.label}** phase: {phase.description}. Navigate to tab **{phase.label}** to proceed."

    def go_to_phase(self, phase_name: str) -> str | None:
        """Jump to a specific phase by name. Returns message or None if invalid."""
        if phase_name not in self._phase_map:
            return None
        idx = self._phase_names.index(phase_name)
        self._current_idx = idx
        self._states[phase_name].status = "active"
        phase = self._phases[idx]
        return f"Switched to **{phase.label}** phase: {phase.description}."

    # ---- Schema scoping ----

    def get_phase_fields(self, all_fields: dict[str, dict]) -> dict[str, dict]:
        """Return only the schema fields relevant to the current phase.

        If the current phase has no field_prefixes defined (e.g. monitor,
        observe), returns all fields so the agent can still answer questions.
        """
        prefixes = self.current.field_prefixes
        if not prefixes:
            return all_fields
        return {k: v for k, v in all_fields.items() if k in prefixes}

    # ---- Summary ----

    def status_summary(self) -> str:
        """Return a Markdown summary of all phase statuses."""
        lines = []
        for i, phase in enumerate(self._phases):
            state = self._states[phase.name]
            marker = ">" if i == self._current_idx else " "
            icon = {"pending": "[ ]", "active": "[~]", "complete": "[x]"}[state.status]
            lines.append(f"{marker} {icon} **{phase.label}**: {phase.description}")
        return "\n".join(lines)
