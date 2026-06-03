"""Tests for the technique-manifest layer (P1.a).

See ``MULTI_TECHNIQUE_PLAN.md``. P1.a introduces, additively, the
technique-family plug-in surface above beamlines:

- a lazily-discovered technique registry
- a single-crystal manifest declaring tabs 1-3 (lazy-importing the existing
  app views) plus the tab label/alias and bridged-submodel contract

No app/core code has moved yet, so these tests pin the new surface without
touching the still-flat composition.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

import exphub.beamlines  # noqa: F401 — registers beamlines
from exphub.core.beamline import (
    TabKey,
    TechniqueManifest,
    active_technique,
    get_technique,
    set_active,
)
from exphub.core.beamline.technique import _reset_for_tests

# ---------- registry + lazy discovery ----------


def test_get_technique_lazily_discovers_single_crystal():
    _reset_for_tests()
    manifest = get_technique("single_crystal")
    assert isinstance(manifest, TechniqueManifest)
    assert manifest.id == "single_crystal"


def test_get_technique_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        get_technique("does_not_exist")


def test_active_technique_follows_active_beamline():
    set_active("topaz")
    assert active_technique().id == "single_crystal"
    set_active("corelli")
    assert active_technique().id == "single_crystal"
    set_active("topaz")


# ---------- TabKey contract ----------


def test_tabkey_values_are_stable():
    # The dispatcher + agent depend on these exact string ids; renaming any is
    # a breaking change.
    assert [k.value for k in TabKey] == [
        "ipts",
        "live",
        "steering",
        "status",
        "analysis",
    ]


# ---------- single-crystal manifest shape ----------


def test_single_crystal_declares_default_tabs_1_to_3():
    manifest = get_technique("single_crystal")
    assert set(manifest.default_tabs) == {TabKey.IPTS, TabKey.LIVE, TabKey.STEERING}
    # Tabs 4-5 have no technique default (fall through to beamline/placeholder).
    assert TabKey.STATUS not in manifest.default_tabs
    assert TabKey.ANALYSIS not in manifest.default_tabs


def test_default_tab_factories_take_one_positional_arg():
    """Each factory is called with the active view-model (the TabFactory protocol)."""
    manifest = get_technique("single_crystal")
    for key, factory in manifest.default_tabs.items():
        assert callable(factory), key
        params = list(inspect.signature(factory).parameters.values())
        positional = [
            p
            for p in params
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        assert len(positional) == 1, key


def test_manifest_has_labels_for_all_five_tabs():
    manifest = get_technique("single_crystal")
    assert set(manifest.tab_labels) == set(TabKey)


def test_tab_aliases_resolve_to_valid_tab_keys():
    manifest = get_technique("single_crystal")
    assert manifest.tab_aliases["temporal_analysis"] is TabKey.LIVE
    assert manifest.tab_aliases["angle_plan"] is TabKey.STEERING
    assert all(isinstance(v, TabKey) for v in manifest.tab_aliases.values())


# ---------- invariant #3: bridged_submodels exist on the root model ----------


def test_bridged_submodels_exist_on_main_model():
    from exphub.app.models.main_model import MainModel

    manifest = get_technique("single_crystal")
    model = MainModel()
    for name in manifest.bridged_submodels:
        assert hasattr(model, name), name


def test_manifest_is_frozen():
    manifest = get_technique("single_crystal")
    with pytest.raises(ValidationError):
        manifest.id = "mutated"  # type: ignore[misc]


# ---------- 3-layer prompt composition ----------


def test_composed_prompt_includes_technique_layer():
    from exphub.agent.prompts.composer import compose_system_prompt

    set_active("topaz")
    prompt = compose_system_prompt(task="experiment_steering")
    # core identity, then technique layer, then beamline layer — all present.
    assert "# Core Identity" in prompt
    assert "Technique: Single-Crystal Diffraction" in prompt
    assert "TOPAZ is a single-crystal" in prompt
    # technique fragment precedes the beamline fragment.
    assert prompt.index("Technique: Single-Crystal Diffraction") < prompt.index(
        "TOPAZ is a single-crystal"
    )


# ---------- PhaseManager sourced from the manifest ----------


def test_manifest_carries_single_crystal_phases():
    manifest = get_technique("single_crystal")
    names = [p.name for p in manifest.phases]
    assert names == [
        "setup", "monitor", "plan", "refine_plan", "submit", "observe", "analyse",
    ]


def test_phase_manager_defaults_to_active_technique_phases():
    from exphub.agent.workflow import PhaseManager

    set_active("topaz")
    pm = PhaseManager()
    assert pm.phases == active_technique().phases
    assert pm.current_name == "setup"


def test_phase_manager_accepts_explicit_phases():
    from exphub.agent.workflow import PhaseManager
    from exphub.core.beamline import PhaseDefinition, TabKey

    custom = (
        PhaseDefinition(name="a", tab=TabKey.IPTS, label="A", description="first"),
        PhaseDefinition(name="b", tab=TabKey.LIVE, label="B", description="second"),
    )
    pm = PhaseManager(custom)
    assert pm.phase_names == ["a", "b"]
    assert pm.current_name == "a"


# ---------- navigate_to_tab TabKey shim ----------


def test_navigate_tab_maps_tabkey_to_dispatcher_int():
    from exphub.app.view_models.app_shell import _tab_to_int

    assert _tab_to_int(TabKey.IPTS) == 1
    assert _tab_to_int(TabKey.LIVE) == 2
    assert _tab_to_int(TabKey.STEERING) == 3
    assert _tab_to_int(TabKey.STATUS) == 5
    assert _tab_to_int(TabKey.ANALYSIS) == 6
    # legacy integer addressing passes straight through (shim).
    assert _tab_to_int(3) == 3


# ---------- agent action tools from the manifest ----------


def test_manifest_declares_action_tools():
    manifest = get_technique("single_crystal")
    names = {a.name for a in manifest.action_tools}
    assert names == {
        "submit_angle_plan", "authenticate_eic", "initialize_strategy",
        "upload_strategy", "stop_current_run",
    }
    for spec in manifest.action_tools:
        assert spec.vm_method
        assert spec.description


def test_make_tools_generates_action_tools_from_manifest():
    from exphub.agent.tools import make_tools

    manifest = get_technique("single_crystal")
    calls = []
    fns = {s.name: (lambda s=s: calls.append(s.name)) for s in manifest.action_tools}
    tools = {
        t.name: t
        for t in make_tools({}, action_tools=manifest.action_tools, action_fns=fns)
    }
    assert "submit_angle_plan" in tools
    out = tools["submit_angle_plan"].invoke({})
    assert out["status"] == "ok"
    assert "submit_angle_plan" in calls


def test_action_tool_reports_unavailable_without_callable():
    from exphub.agent.tools import make_tools

    manifest = get_technique("single_crystal")
    tools = {
        t.name: t
        for t in make_tools({}, action_tools=manifest.action_tools, action_fns={})
    }
    out = tools["stop_current_run"].invoke({})
    assert "error" in out


# ---------- Agent.rebuild_schema plumbing ----------


def test_agent_rebuild_schema_refreshes_tools_and_graph():
    from exphub.agent.agent import Agent

    set_active("topaz")
    agent = Agent(schema_properties={"a": {"title": "A"}})
    graph_before = agent.graph
    agent.rebuild_schema({"b": {"title": "B"}})
    assert agent.schema_properties == {"b": {"title": "B"}}
    assert agent.graph is not graph_before  # graph rebuilt
    # generic tool set still present after rebuild
    assert any(t.name == "set_parameter" for t in agent._tools)
