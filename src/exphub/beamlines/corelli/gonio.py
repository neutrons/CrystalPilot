"""CORELLI goniometer / ramp PV definitions.

PV-name prefix is ``BL9:`` (SNS BL-9). Mirrors the structure of TOPAZ's
``gonio.py`` so the legacy ``app/models/gonio_pvs.py`` shim can re-export
either beamline's layout transparently.
"""

from __future__ import annotations

AMBIENT = "Ambient goniometer"
CRYOGENIC = "Cryogenic goniometer"

# Placeholder PV names. Replace with the real CORELLI sample-rotation PVs
# when integrating against the live IOC.
ANGLE_PVS: dict[str, dict[str, str]] = {
    AMBIENT: {
        "omega": "BL9:Mot:Sample:omega",
        "phi": "BL9:Mot:Sample:phi",
    },
    CRYOGENIC: {
        "omega": "BL9:CryoOmega",
    },
}

RAMP_PVS: dict[str, str] = {
    "start": "BL9:SE:Ramp:Start",
    "end": "BL9:SE:Ramp:End",
    "rate": "BL9:SE:Ramp:Rate",
    "soak": "BL9:SE:Ramp:Soak",
    "run": "BL9:SE:Ramp:Run",
}

RAMP_PV_ALIASES: dict[str, list[str]] = {
    "start": ["BL9:SE:Ramp:Start", "RampStart"],
    "end": ["BL9:SE:Ramp:End", "RampEnd"],
    "rate": ["BL9:SE:Ramp:Rate", "RampRate"],
    "soak": ["BL9:SE:Ramp:Soak", "RampSoak"],
    "run": ["BL9:SE:Ramp:Run", "RampRun"],
}

WAIT_FOR_PCHARGE_PV = "BL9:Det:PCharge:C"


def angle_columns(goniometer_type: str) -> list[str]:
    pvs = ANGLE_PVS[goniometer_type]
    if goniometer_type == CRYOGENIC:
        return [pvs["omega"]]
    return [pvs["omega"], pvs["phi"]]


def angle_keys(goniometer_type: str) -> list[str]:
    if goniometer_type == CRYOGENIC:
        return ["omega"]
    return ["omega", "phi"]


def detect_goniometer_type(columns: list[str]) -> str:
    if "BL9:CryoOmega" in columns:
        return CRYOGENIC
    if "BL9:Mot:Sample:omega" in columns or "BL9:Mot:Sample:phi" in columns:
        return AMBIENT
    raise ValueError(
        f"Could not detect CORELLI goniometer type from columns: {columns}."
    )


def ramp_value(row: dict, key: str) -> str:
    for col in RAMP_PV_ALIASES[key]:
        if col in row and str(row[col]).strip():
            return row[col]
    return ""


def is_ramp_row(row: dict) -> bool:
    return any(ramp_value(row, key) for key in RAMP_PVS)
