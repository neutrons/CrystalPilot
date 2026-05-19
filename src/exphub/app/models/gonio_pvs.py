"""Goniometer / ramp PV column definitions — deprecation shim.

Historical entry point for code that needs PV column names for the EIC
run-strategy table (CSV import / export / submission). The literal PV
strings now live with each beamline's plug-in package (see ``beamlines/``);
this module re-exports the active beamline's values so existing callers
keep working during the multi-beamline refactor.

New code should obtain PVs from :class:`exphub.core.beamline.BeamlineContext`
instead.
"""

from __future__ import annotations

import importlib

from ...core.beamline import active as _active_beamline

# Resolve the active beamline's ``gonio`` submodule and re-export every name.
# The active beamline is determined at module import time. Switching beamlines
# at runtime should be done through BeamlineContext directly; this shim is for
# call sites that have not yet been migrated.
_gonio = importlib.import_module(f"exphub.beamlines.{_active_beamline().id}.gonio")

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
