"""Contract test: the steering view-model's trame ``*_bind`` surface.

Every view module addresses the view-model through these ``*_bind`` attribute
names (they are the undocumented public API between view-models and views). P2
physically relocates the single-crystal view-model (``MainViewModel`` →
``SingleCrystalSteeringViewModel``) and the views that consume these binds; this
test pins the names so those moves stay green at every commit — renaming or
dropping one is a breaking change that should fail here first.

See ``MULTI_TECHNIQUE_PLAN.md`` (P1 deliverable 11 / invariant 2).

The VM is built on a uniquely-named trame server so its binding namespace is
isolated from ``test_app``'s ``MainApp()`` (which uses the default singleton
server — building two on the same server collides on the ``controls`` bind).
"""

from __future__ import annotations

import pytest

import exphub.beamlines  # noqa: F401 — registers beamlines
from exphub.core.beamline import active_technique, set_active

# The trame binding namespaces exposed by the single-crystal steering VM.
EXPECTED_BINDS = {
    "model_bind",
    "view_state_bind",
    "experimentinfo_bind",
    "angleplan_bind",
    "eiccontrol_bind",
    "temporalanalysis_bind",
    "dataanalysis_bind",
    "cssstatus_bind",
    "newtabtemplate_bind",
    "temporalanalysis_updatefigure_uncertainty_bind",
    "temporalanalysis_updatefigure_intensity_bind",
    "newtabtemplate_updatefig_bind",
    "angleplan_updatefigure_coverage_bind",
}


@pytest.fixture(scope="module")
def viewmodels():
    from nova.mvvm.trame_binding import TrameBinding
    from trame.app import get_server

    from exphub.app.mvvm_factory import create_viewmodels

    set_active("topaz")
    server = get_server("test_viewmodel_surface", client_type="vue3")
    binding = TrameBinding(server.state)
    return create_viewmodels(binding)


@pytest.fixture(scope="module")
def steering_vm(viewmodels):
    return viewmodels["steering"]


def test_steering_vm_exposes_expected_bind_surface(steering_vm):
    missing = sorted(name for name in EXPECTED_BINDS if not hasattr(steering_vm, name))
    assert not missing, f"steering VM is missing expected binds: {missing}"


def test_bridged_submodel_binds_exist_on_vm(steering_vm):
    """mvvm_factory wires ``{name}_bind`` for each manifest bridged sub-model."""
    for name in active_technique().bridged_submodels:
        assert hasattr(steering_vm, f"{name}_bind"), name


def test_app_shell_vm_exposes_shell_surface(viewmodels):
    """The technique-agnostic shell VM owns the selector/navigation surface."""
    shell = viewmodels["app_shell"]
    assert hasattr(shell, "view_state_bind")
    assert hasattr(shell, "navigate_to_tab")
    assert hasattr(shell, "switch_beamline")
    # Shell view-state carries the chrome fields (tabs + beamline selector).
    for field in ("active_tab", "beamline_id", "beamline_options"):
        assert hasattr(shell.view_state, field), field
