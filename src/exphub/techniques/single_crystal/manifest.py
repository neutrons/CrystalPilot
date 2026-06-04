"""Single-crystal technique manifest.

Declares the tab shapes and agent contract shared by every single-crystal
beamline. The default tab factories lazy-import the technique's own views from
``techniques/single_crystal/views/`` (the P2 move is complete). Lazy imports
keep manifest registration import-cheap and avoid pulling the trame view stack
in at module load.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...core.beamline.technique import (
    ActionTool,
    TabKey,
    TechniqueManifest,
    register_technique,
)
from .agent.eic_row_builder import SINGLE_CRYSTAL_EIC_ROW_BUILDER
from .agent.phases import SINGLE_CRYSTAL_PHASES
from .models.root import SingleCrystalMainModel

# UI-action verbs the agent can trigger. ``vm_method`` is resolved against the
# live view-model by the chat VM (these are MainViewModel methods today; they
# move to the single-crystal steering VM in P2).
_ACTION_TOOLS = (
    ActionTool(
        name="submit_angle_plan",
        vm_method="submit_angle_plan",
        description=(
            "Submit the current angle plan to the EIC for execution. This "
            "authenticates (if not already done) and sends all runs in the "
            "angle plan to the beamline EIC system. Check that the angle plan "
            "is complete and the EIC settings (token, simulation mode, "
            "beamline) are correct before calling this tool."
        ),
        success_message="Angle plan submitted to EIC.",
        requires_confirmation=True,
    ),
    ActionTool(
        name="authenticate_eic",
        vm_method="call_load_token",
        description=(
            "Load the EIC authentication token from the configured token file. "
            "Must be called before submitting angle plans. The token file path "
            "is set in the EIC Control section."
        ),
        success_message="EIC token loaded successfully.",
    ),
    ActionTool(
        name="initialize_strategy",
        vm_method="reset_run",
        description=(
            "Initialize (reset) the experiment strategy / angle plan. Runs the "
            "angle plan optimizer to generate an initial set of goniometer "
            "orientations (phi/omega angles) based on the current experiment "
            "parameters (crystal system, UB matrix, instrument)."
        ),
        success_message="Strategy initialized with optimized angles.",
    ),
    ActionTool(
        name="upload_strategy",
        vm_method="upload_strategy",
        description=(
            "Upload an angle plan strategy from the configured CSV file. Reads "
            "the strategy file (set via the plan_file parameter) and populates "
            "the angle plan table."
        ),
        success_message="Strategy file uploaded and loaded.",
    ),
    ActionTool(
        name="stop_current_run",
        vm_method="stoprun",
        description=(
            "Stop the currently executing EIC scan/run. IMPORTANT: this is a "
            "destructive operation that aborts a running scan — confirm with "
            "the user before calling it. Use when the user wants to stop data "
            "collection early (e.g. sufficient statistics reached)."
        ),
        success_message="Current run stopped.",
        requires_confirmation=True,
    ),
)

_TECHNIQUE_DIR = Path(__file__).resolve().parent

# --- default tab factories (lazy-import the existing app views) -------------
#
# Each factory takes the active view-model and returns the constructed tab
# content, matching the ``TabFactory`` protocol and the css_status override
# idiom that beamline specs already use for per-tab overrides.


def _ipts_tab(view_model: Any) -> Any:
    from .views.experiment_info import ExperimentInfoView

    return ExperimentInfoView(view_model)


def _live_tab(view_model: Any) -> Any:
    from .views.temporal_analysis import TemporalAnalysisView

    return TemporalAnalysisView(view_model)


def _steering_tab(view_model: Any) -> Any:
    from .views.angle_plan import AnglePlanView

    return AnglePlanView(view_model)


def _analysis_tab(view_model: Any) -> Any:
    from .views.data_analysis import DataAnalysisView

    return DataAnalysisView(view_model)


def _build_steering_vm(model: Any, binding: Any, notify_fn: Any = None) -> Any:
    """Lazy factory for the single-crystal steering VM (manifest stays import-cheap).

    Called by ``app/mvvm_factory.create_viewmodels`` so the app shell builds the
    single-crystal orchestration VM without naming the class. Signature mirrors
    the SANS steering VM: ``(root_model, binding, notify_fn=...)``.
    """
    from .view_models.steering import SingleCrystalSteeringViewModel

    return SingleCrystalSteeringViewModel(model, binding, notify_fn=notify_fn)


SINGLE_CRYSTAL = register_technique(
    TechniqueManifest(
        id="single_crystal",
        display_name="Single-Crystal Diffraction",
        # Tabs 1-3 are technique defaults; beamlines may override via
        # BeamlineSpec.tabs. Tabs 4-5 (STATUS, ANALYSIS) have no technique
        # default — they fall through to a beamline tab or a placeholder.
        default_tabs={
            TabKey.IPTS: _ipts_tab,
            TabKey.LIVE: _live_tab,
            TabKey.STEERING: _steering_tab,
        },
        # Tabs 4-5 have no unconditional default. The data-analysis launcher is
        # a "common-useful" default a single-crystal beamline may opt into via
        # BeamlineSpec.optional_tabs; otherwise the slot falls through to a
        # placeholder. STATUS has no shared default — every beamline ships its
        # own Instrument Status (or a placeholder).
        optional_tab_defaults={
            TabKey.ANALYSIS: _analysis_tab,
        },
        # Which BeamlineSpec.tabs (TabOverrides) field the dispatcher reads for a
        # per-beamline override of each slot. The slot names are technique-neutral
        # and TabKey-aligned (ipts/live/steering/status/analysis); the mapping is
        # kept here (not in app/) so the app-shell dispatcher carries no
        # technique-specific slot vocabulary.
        tab_override_slots={
            TabKey.IPTS: "ipts",
            TabKey.LIVE: "live",
            TabKey.STEERING: "steering",
            TabKey.STATUS: "status",
            TabKey.ANALYSIS: "analysis",
        },
        tab_labels={
            TabKey.IPTS: "IPTS Info",
            TabKey.LIVE: "Live Data Processing",
            TabKey.STEERING: "Experiment Steering",
            TabKey.STATUS: "Instrument Status",
            TabKey.ANALYSIS: "Data Analysis",
        },
        # Natural-language aliases the LLM may use → canonical tab key.
        tab_aliases={
            "ipts_info": TabKey.IPTS,
            "ipts": TabKey.IPTS,
            "live_data_processing": TabKey.LIVE,
            "live_data": TabKey.LIVE,
            "temporal_analysis": TabKey.LIVE,
            "experiment_steering": TabKey.STEERING,
            "angle_plan": TabKey.STEERING,
            "instrument_status": TabKey.STATUS,
            "css_status": TabKey.STATUS,
            "data_analysis": TabKey.ANALYSIS,
        },
        # Sub-models the agent bridges onto the schema. Authoritative here; the
        # agent's bridge module starts reading this in P1.b.
        bridged_submodels=("experimentinfo", "angleplan", "eiccontrol", "dataanalysis"),
        # Authoritative sub-model for fields that appear in more than one.
        field_owner={"point_group": "experimentinfo", "instrument": "experimentinfo"},
        # Technique-level prompt fragment, inserted between core identity and
        # the beamline context by the 3-layer composer.
        prompts_dir=_TECHNIQUE_DIR / "prompts",
        # Experiment phase sequence consumed by the agent's PhaseManager.
        phases=SINGLE_CRYSTAL_PHASES,
        # UI-action verbs the agent can trigger (submit/authenticate/...).
        action_tools=_ACTION_TOOLS,
        # Per-technique EIC row builder (P3a.2): the submit path resolves this
        # via active_technique().eic_row_builder to turn the angle plan into
        # EIC table-scan jobs, keeping core/eic technique-agnostic.
        eic_row_builder=SINGLE_CRYSTAL_EIC_ROW_BUILDER,
        # Contributes the single-crystal composite root to the app shell.
        root_model_factory=SingleCrystalMainModel,
        # Builds the single-crystal steering VM the app shell wires its tabs /
        # chat to (mirrors the SANS manifest).
        steering_vm_factory=_build_steering_vm,
    )
)
