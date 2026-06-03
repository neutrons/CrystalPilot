"""Goniometer / ramp PV column definitions — deprecation shim.

Historical entry point for code that needs PV column names for the EIC
run-strategy table (CSV import / export / submission). The literal PV
strings now live with each beamline's plug-in package (see ``beamlines/``);
this module re-exports the active beamline's values so existing callers
keep working during the multi-beamline refactor.

New code should obtain PVs from :class:`exphub.core.beamline.BeamlineContext`
instead. When the active beamline has no ``gonio`` submodule (e.g. SANS
instruments such as USANS), this shim falls back to empty stubs so
importing the module does not crash at module-load time — single-crystal
call sites that hit the stubs will fail at the use site with a clear
error rather than at startup.
"""

from __future__ import annotations

import importlib
import logging
from types import SimpleNamespace
from typing import Any

from ....core.beamline import active as _active_beamline

_log = logging.getLogger(__name__)


def _empty_stub() -> SimpleNamespace:
    """Return a stub gonio module so import never raises.

    Single-crystal callers that try to read e.g. ``ANGLE_PVS`` get empty
    structures instead of strings; downstream code that iterates the dict
    sees an empty plan rather than crashing the app at startup.
    """
    def _angle_columns(_goniometer_type: str) -> list[str]:
        return []

    def _angle_keys(_goniometer_type: str) -> list[str]:
        return []

    def _detect_goniometer_type(_columns: list[str]) -> str:
        return "none"

    def _ramp_value(_row: dict, _key: str) -> str:
        return ""

    def _is_ramp_row(_row: dict) -> bool:
        return False

    return SimpleNamespace(
        AMBIENT="",
        CRYOGENIC="",
        ANGLE_PVS={},
        RAMP_PVS={},
        RAMP_PV_ALIASES={},
        WAIT_FOR_PCHARGE_PV="",
        angle_columns=_angle_columns,
        angle_keys=_angle_keys,
        detect_goniometer_type=_detect_goniometer_type,
        ramp_value=_ramp_value,
        is_ramp_row=_is_ramp_row,
    )


try:
    _gonio: Any = importlib.import_module(
        f"exphub.beamlines.{_active_beamline().id}.gonio"
    )
except ModuleNotFoundError:
    _log.info(
        "Active beamline %r has no gonio module — using empty stubs. "
        "Single-crystal features (angle plan, EIC submission) will not "
        "function until a beamline with a gonio module is active.",
        _active_beamline().id,
    )
    _gonio = _empty_stub()

AMBIENT = _gonio.AMBIENT
CRYOGENIC = _gonio.CRYOGENIC
ANGLE_PVS = _gonio.ANGLE_PVS
RAMP_PVS = _gonio.RAMP_PVS
RAMP_PV_ALIASES = _gonio.RAMP_PV_ALIASES
WAIT_FOR_PCHARGE_PV = _gonio.WAIT_FOR_PCHARGE_PV
angle_columns = _gonio.angle_columns
angle_keys = _gonio.angle_keys
detect_goniometer_type = _gonio.detect_goniometer_type
ramp_value = _gonio.ramp_value
is_ramp_row = _gonio.is_ramp_row

__all__ = [
    "AMBIENT",
    "ANGLE_PVS",
    "CRYOGENIC",
    "RAMP_PV_ALIASES",
    "RAMP_PVS",
    "WAIT_FOR_PCHARGE_PV",
    "angle_columns",
    "angle_keys",
    "detect_goniometer_type",
    "is_ramp_row",
    "ramp_value",
]
