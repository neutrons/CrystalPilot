"""End-to-end multi-technique gate (P4.4).

See ``MULTI_TECHNIQUE_PLAN.md`` — the P4 test gate pins the three behaviours
that make "one app, several technique families" real:

- ``set_active("topaz")`` (a single-crystal beamline) → the tab-1 (IPTS-Info)
  model carries ``crystalsystem`` (crystallography surface present).
- ``set_active("<usans-stub>")`` (a ``technique="sans"`` beamline) → the tab-1
  model has **no** ``crystalsystem`` (no reciprocal-lattice machinery).
- Cross-technique switching is gated to a restart: the app-shell beamline
  selector grays out cross-technique options and ``switch_beamline`` refuses a
  programmatic cross-technique switch with the restart banner.

The real USANS beamline spec lands in P5; here we register a *minimal in-test
stub* spec (``technique_config=SansConfig()``) so the gate exercises the SANS
technique manifest + root model that P4 already shipped. The whole flow runs
through the production seams (technique registry → ``root_model_factory`` →
agent bridge snapshot → app-shell selector), so this is a true end-to-end
check, not a shape assertion against a hand-built model.
"""

from __future__ import annotations

import pytest

import exphub.beamlines  # noqa: F401 — registers TOPAZ + CORELLI
from exphub.agent.bridge import bridged_submodels, snapshot_models
from exphub.app.models.main_model import MainModel
from exphub.core.beamline import (
    BeamlineSpec,
    SansConfig,
    active,
    active_technique,
    register,
    set_active,
)
from exphub.core.beamline.registry import _REGISTRY

# Id of the throwaway SANS beamline used as the USANS stand-in until P5.
_USANS_STUB_ID = "_usans_stub"


@pytest.fixture
def usans_stub():
    """Register a minimal ``technique="sans"`` beamline, then deregister it.

    Stands in for the real USANS spec (P5). A bare ``SansConfig()`` is enough to
    route the registry/technique layer to the SANS manifest + ``SansMainModel``;
    no PVs/paths are needed for the tab-shape + gating assertions here.
    """
    spec = BeamlineSpec(
        id=_USANS_STUB_ID,
        display_name="USANS (stub)",
        technique_config=SansConfig(),
    )
    register(spec)
    try:
        yield spec
    finally:
        _REGISTRY.pop(_USANS_STUB_ID, None)
        set_active("topaz")


def _active_tab1_model():
    """Build the active technique's tab-1 (IPTS-Info) model via production seams.

    Resolves the technique's root model through the manifest's
    ``root_model_factory`` (single-crystal leaves it ``None`` and is served by
    the app's ``MainModel``), then returns the *first* bridged sub-model — the
    IPTS-Info / sample-info model that backs tab 1 for every technique.
    """
    manifest = active_technique()
    factory = manifest.root_model_factory or MainModel
    root = factory()
    tab1_field = bridged_submodels()[0]
    return getattr(root, tab1_field)


def _active_tab1_snapshot() -> dict:
    """Flat agent-facing snapshot of the active technique's tab-1 model.

    Uses the same ``snapshot_models`` path the agent's ``set_parameter`` surface
    is built from, so "has ``crystalsystem``" means "the agent can see and set
    it" — the behaviour the gate actually cares about.
    """
    manifest = active_technique()
    factory = manifest.root_model_factory or MainModel
    return snapshot_models(factory())


# --------------------------- tab-1 model shape -------------------------------


def test_single_crystal_tab1_has_crystalsystem():
    """A single-crystal beamline exposes the crystallography surface on tab 1."""
    set_active("topaz")
    assert active_technique().id == "single_crystal"

    tab1 = _active_tab1_model()
    assert "crystalsystem" in type(tab1).model_fields
    # And it is visible through the agent bridge (set_parameter surface).
    assert "crystalsystem" in _active_tab1_snapshot()


def test_sans_tab1_has_no_crystalsystem(usans_stub):
    """A ``technique="sans"`` beamline drops all crystallography from tab 1."""
    set_active(_USANS_STUB_ID)
    assert active().technique == "sans"
    assert active_technique().id == "sans"

    tab1 = _active_tab1_model()
    # No crystal system / point group / centering / UB on the SANS IPTS model.
    fields = set(type(tab1).model_fields)
    assert "crystalsystem" not in fields
    assert "point_group" not in fields
    assert "centering" not in fields
    assert "UB" not in fields
    # ...and it never reaches the agent's flat snapshot either.
    assert "crystalsystem" not in _active_tab1_snapshot()


def test_techniques_differ_on_the_same_tab_slot(usans_stub):
    """The same tab slot resolves to differently-shaped models per technique."""
    set_active("topaz")
    sc_fields = set(type(_active_tab1_model()).model_fields)

    set_active(_USANS_STUB_ID)
    sans_fields = set(type(_active_tab1_model()).model_fields)

    # Both keep the shared experiment-identity surface...
    assert {"exp_name", "ipts_number", "instrument"} <= sc_fields
    assert {"exp_name", "ipts_number", "instrument"} <= sans_fields
    # ...but only single-crystal carries the lattice fields.
    assert "crystalsystem" in sc_fields
    assert "crystalsystem" not in sans_fields


# --------------------------- cross-technique gating --------------------------


def test_cross_technique_selector_option_disabled(usans_stub):
    """With single-crystal active, the SANS beamline's selector option is gated."""
    from exphub.app.view_models.app_shell import _default_beamline_options

    set_active("topaz")
    by_id = {o["value"]: o for o in _default_beamline_options()}

    # Same-technique beamlines stay selectable.
    assert by_id["topaz"]["disabled"] is False
    assert by_id["corelli"]["disabled"] is False
    # The cross-technique (SANS) beamline is grayed out.
    assert by_id[_USANS_STUB_ID]["disabled"] is True


def test_cross_technique_switch_refused_with_banner(usans_stub):
    """``switch_beamline`` refuses a cross-technique switch and surfaces the banner."""
    from nova.mvvm.trame_binding import TrameBinding
    from trame.app import get_server

    from exphub.app.view_models.app_shell import AppShellViewModel

    set_active("topaz")
    server = get_server("test_multi_technique_refuse", client_type="vue3")
    shell = AppShellViewModel(TrameBinding(server.state))

    shell.switch_beamline(_USANS_STUB_ID)

    # Registry unchanged, selector rolled back, restart banner surfaced.
    assert active().id == "topaz"
    assert shell.view_state.beamline_id == "topaz"
    assert shell.view_state.beamline_switch_visible is True
    assert "Restart CrystalPilot to switch technique families" in (
        shell.view_state.beamline_switch_notice
    )


def test_same_technique_switch_not_gated(usans_stub):
    """Sanity: an inside-technique switch (TOPAZ→CORELLI) is *not* gated."""
    from exphub.app.view_models.app_shell import _default_beamline_options

    set_active("topaz")
    by_id = {o["value"]: o for o in _default_beamline_options()}
    # CORELLI is single-crystal like TOPAZ — selectable, not grayed out.
    assert by_id["corelli"]["disabled"] is False
