"""Scientific cross-field validation for CrystalPilot agent.

Encodes crystallographic domain knowledge:
- Crystal system → valid point groups
- Point group → valid centering types
- Unit cell volume sanity check (atoms × Z × 10 Å³ minimum)

Ported from NeuDiff-Agent.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Crystal system → point group → centering cascade
# ---------------------------------------------------------------------------

CRYSTAL_SYSTEM_POINT_GROUP_MAP: dict[str, list[str]] = {
    "Triclinic": ["1", "-1"],
    "Monoclinic": ["2", "m", "2/m", "112", "11m", "112/m"],
    "Orthorhombic": ["222", "mm2", "mmm"],
    "Tetragonal": ["4", "-4", "4/m", "422", "4mm", "-42m", "-4m2", "4/mmm"],
    "Trigonal/Rhombohedral": ["3 r", "-3 r", "32 r", "3m r", "-3m r"],
    "Trigonal/Hexagonal": ["3", "-3", "312", "31m", "32", "321", "3m", "-31m", "-3m", "-3m1"],
    "Hexagonal": ["6", "-6", "6/m", "622", "6mm", "-62m", "-6m2", "6/mmm"],
    "Cubic": ["23", "m-3", "432", "-43m", "m-3m"],
}

POINT_GROUP_CENTERING_MAP: dict[str, list[str]] = {
    "1": ["P"],
    "-1": ["P"],
    "2": ["P", "C"],
    "m": ["P", "C"],
    "2/m": ["P", "C"],
    "112": ["P", "C"],
    "11m": ["P", "C"],
    "112/m": ["P", "C"],
    "222": ["P", "I", "C", "A", "B"],
    "mm2": ["P", "I", "C", "A", "B"],
    "mmm": ["P", "I", "C", "A", "B"],
    "4": ["P", "I"],
    "-4": ["P", "I"],
    "4/m": ["P", "I"],
    "422": ["P", "I"],
    "4mm": ["P", "I"],
    "-42m": ["P", "I"],
    "-4m2": ["P", "I"],
    "4/mmm": ["P", "I"],
    "3 r": ["R"],
    "-3 r": ["R"],
    "32 r": ["R"],
    "3m r": ["R"],
    "-3m r": ["R"],
    "3": ["Robv", "Rrev"],
    "-3": ["Robv", "Rrev"],
    "312": ["Robv", "Rrev"],
    "31m": ["Robv", "Rrev"],
    "32": ["Robv", "Rrev"],
    "321": ["Robv", "Rrev"],
    "3m": ["Robv", "Rrev"],
    "-31m": ["Robv", "Rrev"],
    "-3m": ["Robv", "Rrev"],
    "-3m1": ["Robv", "Rrev"],
    "6": ["P"],
    "-6": ["P"],
    "6/m": ["P"],
    "622": ["P"],
    "6mm": ["P"],
    "-62m": ["P"],
    "-6m2": ["P"],
    "6/mmm": ["P"],
    "23": ["P", "I", "F"],
    "m-3": ["P", "I", "F"],
    "432": ["P", "I", "F"],
    "-43m": ["P", "I", "F"],
    "m-3m": ["P", "I", "F"],
}


def validate_point_group(point_group: str, crystal_system: str | None) -> str | None:
    """Return an error message if *point_group* is invalid for *crystal_system*, else None."""
    if not crystal_system:
        return None
    valid = CRYSTAL_SYSTEM_POINT_GROUP_MAP.get(crystal_system, [])
    if not valid:
        return None  # unknown crystal system — skip validation
    if point_group not in valid:
        opts = ", ".join(valid)
        return (
            f"Point group **{point_group}** is not valid for crystal system **{crystal_system}**. Valid options: {opts}"
        )
    return None


def validate_centering(centering: str, point_group: str | None) -> str | None:
    """Return an error message if *centering* is invalid for *point_group*, else None."""
    if not point_group:
        return None
    valid = POINT_GROUP_CENTERING_MAP.get(point_group, [])
    if not valid:
        return None  # unknown point group — skip validation
    if centering not in valid:
        opts = ", ".join(valid)
        return f"Centering **{centering}** is not valid for point group **{point_group}**. Valid options: {opts}"
    return None


def dependent_fields_to_reset(changed_key: str) -> list[str]:
    """Return field names that should be cleared when *changed_key* changes.

    Crystal system → point_group → centering is a strict cascade:
    changing an upstream field invalidates downstream choices.
    """
    if changed_key == "crystalsystem":
        return ["point_group", "centering"]
    if changed_key == "point_group":
        return ["centering"]
    return []


# ---------------------------------------------------------------------------
# Unit cell volume sanity check
# ---------------------------------------------------------------------------


def _count_atoms(formula: str) -> int:
    """Count total atoms in a chemical formula, e.g. 'C6H12O6' → 24."""
    formula = formula.replace(" ", "")
    tokens = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    return sum(int(n or 1) for _, n in tokens)


def check_unit_cell_volume(config_state: dict[str, Any]) -> tuple[bool, str]:
    """Validate that unit_cell_volume is physically reasonable.

    Returns (is_error, message).  ``is_error`` is True when the volume is
    unrealistically small given the molecular formula and Z.
    """
    formula = str(config_state.get("molecular_formula", "")).strip()
    z_val = config_state.get("Z")
    volume = config_state.get("unit_cell_volume")

    if not formula or z_val is None or volume is None:
        return False, ""

    try:
        z_val = float(z_val)
        volume = float(volume)
    except (ValueError, TypeError):
        return False, ""

    if z_val <= 0:
        return True, "Z must be >= 1. Please re-enter."

    atoms = _count_atoms(formula)
    if atoms == 0:
        return False, ""

    threshold = atoms * z_val * 10
    if volume < threshold:
        return True, (
            f"Unit cell volume {volume} Angstrom^3 seems unrealistically small. "
            f"With {atoms} atoms and Z={z_val:.0f}, expect at least "
            f"~{threshold:.0f} Angstrom^3 (atoms x Z x 10). Please double-check."
        )
    return False, ""
