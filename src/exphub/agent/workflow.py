"""Lightweight experiment-phase state machine for CrystalPilot.

Tracks which phase of the experiment the user is in, scopes schema
fields per phase, and provides confirmation gates between phases.

Inspired by NeuDiff-Agent's PhaseManager but adapted to CrystalPilot's
7-phase experiment workflow with tab-based navigation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase definitions — maps each phase to its UI tab and relevant fields
# ---------------------------------------------------------------------------

@dataclass
class PhaseDefinition:
    """Static definition of an experiment phase."""
    name: str
    tab: int          # CrystalPilot tab number for navigation
    tab_name: str     # Human-readable tab label
    description: str  # What the user does in this phase
    field_prefixes: tuple[str, ...] = ()  # Schema field name prefixes scoped to this phase


# The 7 CrystalPilot phases in order
PHASES: list[PhaseDefinition] = [
    PhaseDefinition(
        name="setup",
        tab=1,
        tab_name="IPTS Info",
        description="Enter experiment metadata: IPTS, crystal system, sample info",
        field_prefixes=(
            "ipts_number", "exp_name", "instrument", "molecular_formula", "Z",
            "unit_cell_volume", "sample_radius", "crystalsystem", "centering",
            "point_group", "cal_filename", "data_directory", "base_dir",
            "read_ub", "UBFileName",
        ),
    ),
    PhaseDefinition(
        name="monitor",
        tab=2,
        tab_name="Live Data Processing",
        description="Stream live reduction results and confirm data quality",
    ),
    PhaseDefinition(
        name="plan",
        tab=3,
        tab_name="Experiment Steering",
        description="Generate an initial angle plan for reciprocal space coverage",
        field_prefixes=(
            "max_q", "num_peaks_to_find", "tolerance", "predict_peaks",
            "peak_radius", "bkg_inner_radius", "bkg_outer_radius",
            "pred_min_dspacing", "pred_max_dspacing",
            "pred_min_wavelength", "pred_max_wavelength",
            "abc_min", "abc_max", "edge_pixels", "split_threshold",
            "ellipse_size_specified", "subtract_bkg", "background_filename",
        ),
    ),
    PhaseDefinition(
        name="refine_plan",
        tab=3,
        tab_name="Experiment Steering",
        description="Edit the angle plan — add, remove, or modify runs",
        field_prefixes=("angle_list_pd",),
    ),
    PhaseDefinition(
        name="submit",
        tab=3,
        tab_name="EIC Control",
        description="Submit the angle plan to EIC for execution",
    ),
    PhaseDefinition(
        name="observe",
        tab=5,
        tab_name="Instrument Status",
        description="Monitor motor positions and scan progress",
    ),
    PhaseDefinition(
        name="analyse",
        tab=6,
        tab_name="Data Analysis",
        description="Run data reduction and analysis on collected runs",
        field_prefixes=(
            "spectra_filename", "norm_to_wavelength", "scale_factor",
            "min_intensity", "min_isigi", "z_score", "border_pixels",
            "min_dspacing", "max_dspacing", "min_wavelength", "max_wavelength",
            "starting_batch_number", "SAFile", "FluxFile",
            "index_satellite_peaks", "mod_vec_1", "mod_vec_2", "mod_vec_3",
            "mod_vec_1_dh", "mod_vec_1_dk", "mod_vec_1_dl",
            "mod_vec_2_dh", "mod_vec_2_dk", "mod_vec_2_dl",
            "mod_vec_3_dh", "mod_vec_3_dk", "mod_vec_3_dl",
            "max_order", "cross_terms", "save_mod_info",
            "tolerance_satellite",
            "sat_peak_radius", "sat_peak_region_radius",
            "sat_peak_inner_radius", "sat_peak_outer_radius",
        ),
    ),
]

PHASE_NAMES = [p.name for p in PHASES]
_PHASE_MAP = {p.name: p for p in PHASES}


# ---------------------------------------------------------------------------
# Phase state (runtime, per-phase)
# ---------------------------------------------------------------------------

@dataclass
class PhaseState:
    """Runtime state for a single phase."""
    status: str = "pending"    # pending | active | complete
    pending_confirm: bool = False  # waiting for user to confirm advancing


# ---------------------------------------------------------------------------
# PhaseManager
# ---------------------------------------------------------------------------

class PhaseManager:
    """Tracks the current experiment phase and manages transitions.

    The manager enforces a linear phase sequence with confirmation gates:
    a phase must be explicitly completed before advancing to the next.
    """

    def __init__(self) -> None:
        self._current_idx: int = 0
        self._states: dict[str, PhaseState] = {name: PhaseState() for name in PHASE_NAMES}
        self._states[PHASE_NAMES[0]].status = "active"

    # ---- Properties ----

    @property
    def current(self) -> PhaseDefinition:
        """Return the definition of the current phase."""
        return PHASES[self._current_idx]

    @property
    def current_name(self) -> str:
        return PHASES[self._current_idx].name

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
        if self._current_idx + 1 >= len(PHASES):
            return None  # all phases done
        self.current_state.pending_confirm = True
        next_phase = PHASES[self._current_idx + 1]
        return (
            f"**{self.current.tab_name}** phase complete. "
            f"Ready to move to **{next_phase.tab_name}** ({next_phase.description})? "
            f"Say **yes** to continue."
        )

    def advance(self) -> str:
        """Advance to the next phase (call after user confirms).

        Returns a guidance message about the new phase.
        """
        self.current_state.pending_confirm = False
        if self._current_idx + 1 >= len(PHASES):
            return "All experiment phases are complete."
        self._current_idx += 1
        self.current_state.status = "active"
        phase = self.current
        return (
            f"Now in **{phase.tab_name}** phase: {phase.description}. "
            f"Navigate to tab **{phase.tab_name}** to proceed."
        )

    def go_to_phase(self, phase_name: str) -> str | None:
        """Jump to a specific phase by name. Returns message or None if invalid."""
        if phase_name not in _PHASE_MAP:
            return None
        idx = PHASE_NAMES.index(phase_name)
        self._current_idx = idx
        self._states[phase_name].status = "active"
        phase = PHASES[idx]
        return f"Switched to **{phase.tab_name}** phase: {phase.description}."

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
        for i, phase in enumerate(PHASES):
            state = self._states[phase.name]
            marker = ">" if i == self._current_idx else " "
            icon = {"pending": "[ ]", "active": "[~]", "complete": "[x]"}[state.status]
            lines.append(f"{marker} {icon} **{phase.tab_name}**: {phase.description}")
        return "\n".join(lines)
