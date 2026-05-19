"""TOPAZ goniometer / ramp / charge PV definitions.

This file owns the TOPAZ-specific PV strings used by the angle-plan CSV
import/export and EIC submission paths. It is consumed by the
``app/models/gonio_pvs.py`` shim during the multi-beamline transition;
future phases will delete that shim and route every call site through
:class:`BeamlineContext`.
"""

from __future__ import annotations

AMBIENT = "Ambient goniometer"
CRYOGENIC = "Cryogenic goniometer"

ANGLE_PVS: dict[str, dict[str, str]] = {
    AMBIENT: {
        "omega": "BL12:Mot:goniokm:omega",
        "phi": "BL12:Mot:goniokm:phi",
    },
    CRYOGENIC: {
        "omega": "CryoOmega",
    },
}

RAMP_PVS: dict[str, str] = {
    "start": "BL12:SE:Ramp:Start",
    "end": "BL12:SE:Ramp:End",
    "rate": "BL12:SE:Ramp:Rate",
    "soak": "BL12:SE:Ramp:Soak",
    "run": "BL12:SE:Ramp:Run",
}

# Bare column-name aliases accepted on import (some EIC plan files
# omit the BL12:SE:Ramp: prefix). Always EMIT canonical RAMP_PVS names.
RAMP_PV_ALIASES: dict[str, list[str]] = {
    "start": ["BL12:SE:Ramp:Start", "RampStart"],
    "end": ["BL12:SE:Ramp:End", "RampEnd"],
    "rate": ["BL12:SE:Ramp:Rate", "RampRate"],
    "soak": ["BL12:SE:Ramp:Soak", "RampSoak"],
    "run": ["BL12:SE:Ramp:Run", "RampRun"],
}

WAIT_FOR_PCHARGE_PV = "BL12:Det:PCharge:C"


def angle_columns(goniometer_type: str) -> list[str]:
    """Ordered PV column names for the given goniometer's angle axes."""
    pvs = ANGLE_PVS[goniometer_type]
    if goniometer_type == CRYOGENIC:
        return [pvs["omega"]]
    return [pvs["omega"], pvs["phi"]]


def angle_keys(goniometer_type: str) -> list[str]:
    """Internal RunPlan field names corresponding to :func:`angle_columns`."""
    if goniometer_type == CRYOGENIC:
        return ["omega"]
    return ["omega", "phi"]


def detect_goniometer_type(columns: list[str]) -> str:
    """Infer goniometer type from a CSV's column headers."""
    if "CryoOmega" in columns:
        return CRYOGENIC
    if "BL12:Mot:goniokm:omega" in columns or "BL12:Mot:goniokm:phi" in columns:
        return AMBIENT
    raise ValueError(
        f"Could not detect goniometer type from columns: {columns}. "
        f"Expected one of {list(ANGLE_PVS[AMBIENT].values())} "
        f"or {list(ANGLE_PVS[CRYOGENIC].values())}."
    )


def ramp_value(row: dict, key: str) -> str:
    """Read a ramp field from a CSV row, trying canonical name then aliases."""
    for col in RAMP_PV_ALIASES[key]:
        if col in row and str(row[col]).strip():
            return row[col]
    return ""


def is_ramp_row(row: dict) -> bool:
    """A row is a ramp row iff any ramp column has a non-empty value."""
    return any(ramp_value(row, key) for key in RAMP_PVS)
