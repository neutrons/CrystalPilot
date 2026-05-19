"""PV column-name constants for the EIC run-strategy table.

Centralized here so import / export / submit paths all agree on the
EPICS process-variable names that map to each plan-table column.
"""

from typing import Dict, List

AMBIENT = "Ambient goniometer"
CRYOGENIC = "Cryogenic goniometer"

ANGLE_PVS: Dict[str, Dict[str, str]] = {
    AMBIENT: {
        "omega": "BL12:Mot:goniokm:omega",
        "phi": "BL12:Mot:goniokm:phi",
    },
    CRYOGENIC: {
        "omega": "CryoOmega",
    },
}

RAMP_PVS: Dict[str, str] = {
    "start": "BL12:SE:Ramp:Start",
    "end": "BL12:SE:Ramp:End",
    "rate": "BL12:SE:Ramp:Rate",
    "soak": "BL12:SE:Ramp:Soak",
    "run": "BL12:SE:Ramp:Run",
}

# Bare column-name aliases accepted on import (some EIC plan files
# omit the BL12:SE:Ramp: prefix). Always EMIT canonical RAMP_PVS names.
RAMP_PV_ALIASES: Dict[str, List[str]] = {
    "start": ["BL12:SE:Ramp:Start", "RampStart"],
    "end": ["BL12:SE:Ramp:End", "RampEnd"],
    "rate": ["BL12:SE:Ramp:Rate", "RampRate"],
    "soak": ["BL12:SE:Ramp:Soak", "RampSoak"],
    "run": ["BL12:SE:Ramp:Run", "RampRun"],
}

WAIT_FOR_PCHARGE_PV = "BL12:Det:PCharge:C"


def angle_columns(goniometer_type: str) -> List[str]:
    """Ordered PV column names for the given goniometer's angle axes."""
    pvs = ANGLE_PVS[goniometer_type]
    if goniometer_type == CRYOGENIC:
        return [pvs["omega"]]
    return [pvs["omega"], pvs["phi"]]


def angle_keys(goniometer_type: str) -> List[str]:
    """Internal RunPlan field names corresponding to angle_columns()."""
    if goniometer_type == CRYOGENIC:
        return ["omega"]
    return ["omega", "phi"]


def detect_goniometer_type(columns: List[str]) -> str:
    """Infer goniometer type from a CSV's column headers."""
    if "CryoOmega" in columns:
        return CRYOGENIC
    if "BL12:Mot:goniokm:omega" in columns or "BL12:Mot:goniokm:phi" in columns:
        return AMBIENT
    raise ValueError(
        f"Could not detect goniometer type from columns: {columns}. "
        f"Expected one of {ANGLE_PVS[AMBIENT].values()} or {ANGLE_PVS[CRYOGENIC].values()}."
    )


def ramp_value(row: Dict, key: str) -> str:
    """Read a ramp field from a CSV row, trying canonical name then aliases."""
    for col in RAMP_PV_ALIASES[key]:
        if col in row and str(row[col]).strip():
            return row[col]
    return ""


def is_ramp_row(row: Dict) -> bool:
    """A row is a ramp row iff any ramp column has a non-empty value."""
    return any(ramp_value(row, key) for key in RAMP_PVS)
