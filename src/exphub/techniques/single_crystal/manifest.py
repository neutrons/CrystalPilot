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
from .agent.phases import SINGLE_CRYSTAL_PHASES

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
        # knowledge_dir / eic_row_builder / root_model_factory are wired to
        # their consumers in later steps (P1.b RAG / P3a EIC).
    )
)
