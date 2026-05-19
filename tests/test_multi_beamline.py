"""End-to-end tests for the multi-beamline abstraction.

Verifies that:
- Both shipped beamlines (TOPAZ + CORELLI) register
- ``active()`` returns TOPAZ by default (first-registered wins)
- ``set_active()`` swaps PV/path/preset accessors
- Each beamline's prompt fragment lands in the composed system prompt
"""

from __future__ import annotations

import exphub.beamlines  # noqa: F401 — triggers registration
from exphub.agent.prompts.composer import compose_system_prompt, describe_active_context
from exphub.core.beamline import BeamlineContext, active, get, list_ids, set_active


def test_both_beamlines_registered():
    ids = list_ids()
    assert "topaz" in ids
    assert "corelli" in ids


def test_topaz_is_default_active():
    set_active("topaz")
    assert active().id == "topaz"


def test_set_active_swaps_pvs_and_paths():
    set_active("topaz")
    topaz_ctx = BeamlineContext(active())
    assert topaz_ctx.angle_pv("omega") == "BL12:Mot:goniokm:omega"
    assert topaz_ctx.ipts_root(35036) == "/SNS/TOPAZ/IPTS-35036"
    assert topaz_ctx.eic_dropbox_dir(35036) == "/SNS/groups/topaz/bl_12/IPTS-35036"

    set_active("corelli")
    corelli_ctx = BeamlineContext(active())
    assert corelli_ctx.angle_pv("omega") == "BL9:Mot:Sample:omega"
    assert corelli_ctx.ipts_root(12345) == "/SNS/CORELLI/IPTS-12345"
    assert corelli_ctx.eic_dropbox_dir(12345) == "/SNS/groups/corelli/bl_9/IPTS-12345"

    # Restore TOPAZ for other tests
    set_active("topaz")


def test_set_active_swaps_presets():
    set_active("topaz")
    assert "topaz_standard" in active().agent.presets

    set_active("corelli")
    assert "corelli_standard" in active().agent.presets
    assert "topaz_standard" not in active().agent.presets

    set_active("topaz")


def test_prompt_composer_includes_active_beamline_context():
    set_active("topaz")
    topaz_prompt = compose_system_prompt(task="experiment_steering")
    assert "TOPAZ is a single-crystal" in topaz_prompt
    assert "CORELLI is the elastic" not in topaz_prompt

    set_active("corelli")
    corelli_prompt = compose_system_prompt(task="experiment_steering")
    assert "CORELLI is the elastic" in corelli_prompt
    assert "TOPAZ is a single-crystal" not in corelli_prompt

    # Both share the core identity
    assert "# Core Identity" in topaz_prompt
    assert "# Core Identity" in corelli_prompt

    set_active("topaz")


def test_describe_active_context():
    set_active("topaz")
    line = describe_active_context(task="experiment_steering")
    assert "TOPAZ" in line
    assert "experiment_steering" in line

    set_active("corelli")
    line = describe_active_context(task="data_processing")
    assert "CORELLI" in line
    assert "data_processing" in line

    set_active("topaz")


def test_agent_presets_aggregate_from_registry():
    from exphub.agent.constants import get_experiment_presets

    presets = get_experiment_presets()
    assert "topaz_standard" in presets
    assert "corelli_standard" in presets


def test_corelli_spec_resolves_paths_relative_to_package():
    spec = get("corelli")
    # No BOB screen configured for CORELLI yet — should be None, not crash.
    assert BeamlineContext(spec).bob_screen is None
    # Context-prompt path resolves into the corelli/ package.
    assert "corelli" in str(spec.resolve(spec.agent.context_prompt))
