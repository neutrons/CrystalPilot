"""Startup beamline selection (CLI ``--beamline=`` / ``CRYSTALPILOT_BEAMLINE``).

Live cross-technique switching is gated (the selector grays out beamlines of a
different technique family with a "restart to switch" banner). The restart-time
entry point for those beamlines is the startup picker in ``exphub.app.main``;
these tests pin its precedence and registry effect.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import exphub.beamlines  # noqa: F401 — registers topaz/corelli/usans
from exphub.app.main import _activate_startup_beamline, _resolve_startup_beamline
from exphub.core.beamline import active, set_active


@pytest.fixture(autouse=True)
def restore_active() -> Iterator[None]:
    """Save/restore the module-level active beamline around each test."""
    before = active().id
    yield
    set_active(before)


def test_resolve_precedence_cli_over_env() -> None:
    assert _resolve_startup_beamline(["--beamline=usans"], {}) == "usans"
    assert _resolve_startup_beamline(["beamline=corelli"], {}) == "corelli"
    assert _resolve_startup_beamline([], {"CRYSTALPILOT_BEAMLINE": "usans"}) == "usans"
    # CLI wins over env.
    assert (
        _resolve_startup_beamline(["--beamline=corelli"], {"CRYSTALPILOT_BEAMLINE": "usans"})
        == "corelli"
    )


def test_resolve_none_when_unset() -> None:
    assert _resolve_startup_beamline([], {}) is None
    assert _resolve_startup_beamline(["--port=8080"], {}) is None
    assert _resolve_startup_beamline([], {"CRYSTALPILOT_BEAMLINE": "  "}) is None


def test_activate_env_sets_active() -> None:
    _activate_startup_beamline([], {"CRYSTALPILOT_BEAMLINE": "usans"})
    assert active().id == "usans"
    assert active().technique == "sans"


def test_activate_cli_sets_active() -> None:
    _activate_startup_beamline(["--beamline=corelli"], {})
    assert active().id == "corelli"


def test_activate_unknown_falls_back_without_raising() -> None:
    set_active("topaz")
    _activate_startup_beamline(["--beamline=does-not-exist"], {})
    # Unknown id is ignored; the previously active beamline is unchanged.
    assert active().id == "topaz"


def test_activate_noop_when_unset() -> None:
    set_active("topaz")
    _activate_startup_beamline([], {})
    assert active().id == "topaz"
