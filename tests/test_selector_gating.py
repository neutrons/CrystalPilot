"""Tests for P3.2: cross-technique selector gating + steering on_deactivate.

Two behaviours are pinned here (MULTI_TECHNIQUE_PLAN.md P3 deliverables 4-5):

- The app-shell beamline selector options carry a ``disabled`` flag for any
  beamline whose ``technique`` differs from the active one, so the VSelect
  grays them out and ``switch_beamline`` refuses the switch with a snackbar.
- The single-crystal steering VM's ``on_deactivate`` cancels the live-update
  task and clears temporal buffers before an inside-technique switch.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest

import exphub.beamlines  # noqa: F401 — registers TOPAZ + CORELLI
from exphub.core.beamline import BeamlineSpec, SansConfig, register, set_active
from exphub.core.beamline.registry import _REGISTRY


@pytest.fixture
def sans_stub() -> Iterator[BeamlineSpec]:
    """Register a throwaway SANS-technique beamline, then deregister it."""
    spec = BeamlineSpec(
        id="_sans_stub",
        display_name="SANS Stub",
        technique_config=SansConfig(),
    )
    register(spec)
    try:
        yield spec
    finally:
        _REGISTRY.pop("_sans_stub", None)
        set_active("topaz")


# --------------------------- selector gating ---------------------------------


def test_cross_technique_option_marked_disabled(sans_stub: BeamlineSpec) -> None:
    """With a single-crystal beamline active, the SANS option is disabled."""
    from exphub.app.view_models.app_shell import _default_beamline_options

    set_active("topaz")
    options = _default_beamline_options()
    by_id = {o["value"]: o for o in options}

    # Same-technique beamlines stay enabled.
    assert by_id["topaz"]["disabled"] is False
    assert by_id["corelli"]["disabled"] is False
    # The cross-technique (SANS) beamline is grayed out.
    assert by_id["_sans_stub"]["disabled"] is True


def test_switch_beamline_refuses_cross_technique(sans_stub: BeamlineSpec) -> None:
    """A programmatic cross-technique switch is a no-op + snackbar notice."""
    from nova.mvvm.trame_binding import TrameBinding
    from trame.app import get_server

    from exphub.app.view_models.app_shell import AppShellViewModel
    from exphub.core.beamline import active

    set_active("topaz")
    server = get_server("test_selector_gating_refuse", client_type="vue3")
    shell = AppShellViewModel(TrameBinding(server.state))
    # The bind isn't connected here (TabsPanel does that in the live app);
    # the refusal path's snackbar push is best-effort and tolerates that.

    shell.switch_beamline("_sans_stub")

    # Registry unchanged, selector rolled back, snackbar surfaced.
    assert active().id == "topaz"
    assert shell.view_state.beamline_id == "topaz"
    assert shell.view_state.beamline_switch_visible is True
    assert "Restart CrystalPilot to switch technique families" in (
        shell.view_state.beamline_switch_notice
    )


# --------------------------- on_deactivate -----------------------------------


def test_on_deactivate_cancels_live_update() -> None:
    """on_deactivate stops the live-update task and flips the running flag."""
    from nova.mvvm.trame_binding import TrameBinding
    from trame.app import get_server

    from exphub.app.mvvm_factory import create_viewmodels

    set_active("topaz")
    server = get_server("test_selector_gating_deactivate", client_type="vue3")
    vms = create_viewmodels(TrameBinding(server.state))
    steering = vms["steering"]

    async def _scenario() -> None:
        # Stand in for a running live-update loop.
        async def _never() -> None:
            await asyncio.sleep(3600)

        steering._live_update_task = asyncio.ensure_future(_never())
        steering.view_state.is_live_update_running = True

        steering.on_deactivate()

        assert steering.view_state.is_live_update_running is False
        assert steering._live_update_task is None

    asyncio.run(_scenario())


def test_shell_deactivate_hook_wired_to_steering() -> None:
    """mvvm_factory passes the steering VM's on_deactivate into the shell."""
    from nova.mvvm.trame_binding import TrameBinding
    from trame.app import get_server

    from exphub.app.mvvm_factory import create_viewmodels

    set_active("topaz")
    server = get_server("test_selector_gating_hook", client_type="vue3")
    vms = create_viewmodels(TrameBinding(server.state))
    shell = vms["app_shell"]
    steering = vms["steering"]

    assert shell._deactivate_hook == steering.on_deactivate
