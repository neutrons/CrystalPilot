"""Single-crystal technique manifest.

Declares the tab shapes and agent contract shared by every single-crystal
beamline. In P1.a this lives *additively* alongside the still-in-place
``app/`` code: the default tab factories lazy-import the existing views from
``app/views/`` rather than from a moved-out ``techniques/single_crystal/views/``
package (that physical move is P2). Lazy imports keep manifest registration
import-cheap and avoid pulling the trame view stack in at module load.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...core.beamline.technique import (
    TabKey,
    TechniqueManifest,
    register_technique,
)

_TECHNIQUE_DIR = Path(__file__).resolve().parent

# --- default tab factories (lazy-import the existing app views) -------------
#
# Each factory takes the active view-model and returns the constructed tab
# content, matching the ``TabFactory`` protocol and the css_status override
# idiom that beamline specs already use for per-tab overrides.


def _ipts_tab(view_model: Any) -> Any:
    from ...app.views.experiment_info import ExperimentInfoView

    return ExperimentInfoView(view_model)


def _live_tab(view_model: Any) -> Any:
    from ...app.views.temporal_analysis import TemporalAnalysisView

    return TemporalAnalysisView(view_model)


def _steering_tab(view_model: Any) -> Any:
    from ...app.views.angle_plan import AnglePlanView

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
        # Technique-level prompt fragment, inserted between core identity and
        # the beamline context by the 3-layer composer.
        prompts_dir=_TECHNIQUE_DIR / "prompts",
        # phases / action_tools / knowledge_dir / eic_row_builder /
        # root_model_factory are wired to their consumers in later P1.b steps.
    )
)
