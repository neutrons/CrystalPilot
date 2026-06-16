"""End-to-end multi-technique gate (P4.4, updated P5).

See ``MULTI_TECHNIQUE_PLAN.md`` — this gate pins the behaviours that make "one
app, several technique families" real:

- ``set_active("topaz")`` (a single-crystal beamline) → the tab-1 (IPTS-Info)
  model carries ``crystalsystem`` (crystallography surface present).
- ``set_active("usans")`` (the real ``technique="sans"`` beamline) → the tab-1
  model has **no** ``crystalsystem`` (no reciprocal-lattice machinery).
- Cross-technique switching is gated to a restart: the app-shell beamline
  selector grays out cross-technique options and ``switch_beamline`` refuses a
  programmatic cross-technique switch with the restart banner.
- ``MainApp()`` constructs from a clean env with the USANS (SANS) beamline
  active — the whole composition root (root model + steering VM + tabs) resolves
  through the SANS manifest, not a hardcoded single-crystal path.

P4 used an in-test SANS stub spec; P5 ships the real USANS beamline plug-in
(``beamlines/usans/``), so this gate now drives the production spec. The whole
flow runs through the production seams (beamline registry → technique manifest →
``root_model_factory`` → agent bridge snapshot → app-shell selector → mvvm
factory), so this is a true end-to-end check, not a shape assertion against a
hand-built model.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

import exphub.beamlines  # noqa: F401 — registers TOPAZ + CORELLI + USANS
from exphub.agent.bridge import bridged_submodels, snapshot_models
from exphub.core.beamline import (
    BeamlineSpec,
    active,
    active_technique,
    set_active,
)

# Id of the real USANS beamline plug-in (the first technique="sans" beamline).
_USANS_ID = "usans"


@pytest.fixture
def usans() -> Iterator[BeamlineSpec]:
    """Activate the real USANS beamline, restoring TOPAZ afterwards.

    USANS is a registered plug-in (no in-test registration needed since P5); the
    fixture only resets ``active`` back to a single-crystal default so a test
    that flips the active technique does not leak into the next test.
    """
    try:
        yield set_active(_USANS_ID)
    finally:
        set_active("topaz")


def _active_tab1_model() -> Any:
    """Build the active technique's tab-1 (IPTS-Info) model via production seams.

    Resolves the technique's root model through the manifest's
    ``root_model_factory`` (every technique supplies one), then returns the
    *first* bridged sub-model — the IPTS-Info / sample-info model that backs tab
    1 for every technique.
    """
    manifest = active_technique()
    factory = manifest.root_model_factory
    assert factory is not None
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
    factory = manifest.root_model_factory
    assert factory is not None
    return snapshot_models(factory())


# --------------------------- tab-1 model shape -------------------------------


def test_single_crystal_tab1_has_crystalsystem() -> None:
    """A single-crystal beamline exposes the crystallography surface on tab 1."""
    set_active("topaz")
    assert active_technique().id == "single_crystal"

    tab1 = _active_tab1_model()
    assert "crystalsystem" in type(tab1).model_fields
    # And it is visible through the agent bridge (set_parameter surface).
    assert "crystalsystem" in _active_tab1_snapshot()


def test_sans_tab1_has_no_crystalsystem(usans: BeamlineSpec) -> None:
    """A ``technique="sans"`` beamline drops all crystallography from tab 1."""
    set_active(_USANS_ID)
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


def test_techniques_differ_on_the_same_tab_slot(usans: BeamlineSpec) -> None:
    """The same tab slot resolves to differently-shaped models per technique."""
    set_active("topaz")
    sc_fields = set(type(_active_tab1_model()).model_fields)

    set_active(_USANS_ID)
    sans_fields = set(type(_active_tab1_model()).model_fields)

    # Both keep the shared experiment-identity surface...
    assert {"exp_name", "ipts_number"} <= sc_fields
    assert {"exp_name", "ipts_number"} <= sans_fields
    # ...but only single-crystal carries the lattice fields.
    assert "crystalsystem" in sc_fields
    assert "crystalsystem" not in sans_fields


# --------------------------- cross-technique gating --------------------------


def test_cross_technique_selector_option_disabled(usans: BeamlineSpec) -> None:
    """With single-crystal active, the SANS beamline's selector option is gated."""
    from exphub.app.view_models.app_shell import _default_beamline_options

    set_active("topaz")
    by_id = {o["value"]: o for o in _default_beamline_options()}

    # Same-technique beamlines stay selectable.
    assert by_id["topaz"]["disabled"] is False
    assert by_id["corelli"]["disabled"] is False
    # The cross-technique (SANS) beamline is grayed out.
    assert by_id[_USANS_ID]["disabled"] is True


def test_cross_technique_switch_refused_with_banner(usans: BeamlineSpec) -> None:
    """``switch_beamline`` refuses a cross-technique switch and surfaces the banner."""
    from nova.mvvm.trame_binding import TrameBinding
    from trame.app import get_server

    from exphub.app.view_models.app_shell import AppShellViewModel

    set_active("topaz")
    server = get_server("test_multi_technique_refuse", client_type="vue3")
    shell = AppShellViewModel(TrameBinding(server.state))

    shell.switch_beamline(_USANS_ID)

    # Registry unchanged, selector rolled back, restart banner surfaced.
    assert active().id == "topaz"
    assert shell.view_state.beamline_id == "topaz"
    assert shell.view_state.beamline_switch_visible is True
    assert "Restart CrystalPilot to switch technique families" in (shell.view_state.beamline_switch_notice)


def test_same_technique_switch_not_gated(usans: BeamlineSpec) -> None:
    """Sanity: an inside-technique switch (TOPAZ→CORELLI) is *not* gated."""
    from exphub.app.view_models.app_shell import _default_beamline_options

    set_active("topaz")
    by_id = {o["value"]: o for o in _default_beamline_options()}
    # CORELLI is single-crystal like TOPAZ — selectable, not grayed out.
    assert by_id["corelli"]["disabled"] is False


# --------------------------- app construction (P5) ---------------------------


def test_mainapp_constructs_with_usans_active(usans: BeamlineSpec) -> None:
    """``MainApp()`` builds end-to-end from a clean env with USANS (SANS) active.

    Exercises the composition root under a ``technique="sans"`` beamline: the
    root model, steering VM, and tab panel must all resolve through the SANS
    manifest rather than the hardcoded single-crystal path. A construction that
    does not raise is the assertion (the gate is "MainApp() constructs").

    ``MainApp()`` uses the default singleton trame server and the process-global
    ``bindings_map``; ``test_app`` also builds a ``MainApp()`` there, so we clear
    the global binding map first to isolate this construction (two MainApps on
    the same server otherwise collide on the ``controls`` bind — see
    ``test_viewmodel_surface``'s module docstring).
    """
    from nova.mvvm.bindings_map import bindings_map

    from exphub.app.views.main_view import MainApp

    set_active(_USANS_ID)
    assert active().id == _USANS_ID
    assert active().technique == "sans"

    bindings_map.clear()
    app = MainApp()
    assert app is not None
    # The shell's beamline selector reflects the active USANS beamline.
    assert app.view_models["app_shell"].view_state.beamline_id == _USANS_ID
    # The steering VM resolved to the SANS shape (carries the SANS sub-model
    # binds, not the single-crystal angle-plan ones).
    assert hasattr(app.view_models["steering"], "iptsinfo_bind")
