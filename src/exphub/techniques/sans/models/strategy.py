"""SANS experiment-strategy model (P4.1 skeleton).

The SANS analogue of the single-crystal
:class:`~exphub.techniques.single_crystal.models.angle_plan.AnglePlanModel`
strategy table. It keeps the single-crystal *strategy-CSV row shape*
(``Title``, ``Comment``, ``Wait For``, ``Value`` columns plus a per-step
parameter block) but replaces the goniometer angle columns
(``phi``/``omega``/...) with SANS instrument-configuration columns.

SANS column names are PROVISIONAL — to be confirmed with the SANS scientist
(see ``DECISION DEFAULTS`` in the P4 task brief). The goniometer angle columns
are replaced with these SANS placeholders:

  - ``sample_aperture``     — sample aperture size
  - ``detector_distance``   — sample-to-detector distance
  - ``attenuator``          — attenuator setting
  - ``wavelength_spread``   — wavelength spread (Δλ/λ)

There is no UB matrix, point group, centering, or coverage-polyhedron geometry
here — SANS has no reciprocal lattice to cover.
"""

from __future__ import annotations

import csv
from typing import Any, Dict, List

from pydantic import BaseModel, Field

# Provisional SANS strategy column names. Replace the goniometer angle columns
# of the single-crystal strategy row with SANS instrument-configuration columns.
# column names provisional (TBD with SANS scientist).
SANS_PARAM_COLUMNS: List[str] = [
    "sample_aperture",
    "detector_distance",
    "attenuator",
    "wavelength_spread",
]

# Vuetify data-table header layout for the editable strategy table. Mirrors the
# single-crystal ``_AMBIENT_HEADERS`` shape (Title/Comment ... Wait For/Value/
# Action) with the SANS parameter columns spliced in where the gonio angles
# used to be.
_SANS_HEADERS: List[Dict] = [
    {"title": "Title", "value": "title", "sortable": True, "align": "center"},
    {"title": "Comment", "value": "comment", "sortable": True, "align": "center"},
    *[{"title": col, "value": col, "sortable": True, "align": "center"} for col in SANS_PARAM_COLUMNS],
    {"title": "Wait For", "value": "wait_for", "sortable": True, "align": "center"},
    {"title": "Value", "value": "value", "sortable": True, "align": "center"},
    {"title": "Action", "value": "actions", "sortable": False, "align": "center"},
]


class SansStrategyRow(BaseModel):
    """One SANS strategy step.

    Single-crystal strategy-row shape (``title``/``comment``/``wait_for``/
    ``value`` plus an ``or_time`` fallback) with the goniometer angles replaced by SANS
    instrument-configuration parameters. Column names provisional (TBD with
    SANS scientist).
    """

    title: str = Field(default="Untitled")
    comment: str = Field(default="")
    # --- SANS instrument-configuration parameters (provisional names) -------
    sample_aperture: float = Field(default=0.0, title="Sample Aperture")
    detector_distance: float = Field(default=0.0, title="Detector Distance")
    attenuator: float = Field(default=0.0, title="Attenuator")
    wavelength_spread: float = Field(default=0.0, title="Wavelength Spread")
    # --- single-crystal-shaped wait/value tail -----------------------------
    wait_for: str = Field(default="PCharge")
    value: float = Field(default=0.0)
    or_time: float = Field(default=0.0)


class SansStrategyModel(BaseModel):
    """CSV-loadable, editable SANS strategy table.

    Structural mirror of the single-crystal ``AnglePlanModel`` strategy surface
    (header list, editable row list, plan name/file/type, wait-for options),
    minus all single-crystal geometry (no UB, point group, centering, symmetry
    operations, or coverage polyhedrons).
    """

    # Column keys for the canonical (id-bearing) row dicts the view edits.
    strategy_keys: List[str] = Field(
        default=["id", "title", "comment", *SANS_PARAM_COLUMNS, "wait_for", "value", "or_time"]
    )
    strategy_headers: List[Dict] = Field(default_factory=lambda: list(_SANS_HEADERS))

    # Canonical editable rows (id-bearing dicts) shown in the data table.
    strategy_list: List[Dict] = Field(
        default=[],
        title="SANS Strategy",
        description="List of SANS instrument configurations to measure.",
    )
    # Raw rows as read from a CSV (strategy-row-shaped, SANS columns), before
    # conversion to canonical id-bearing rows. Excluded from state pushes.
    strategy_list_read: List[Dict] = Field(
        default=[],
        title="SANS Strategy (raw)",
        description="Rows as read from the uploaded CSV before normalisation.",
        exclude=True,
    )

    plan_name: str = Field(default="CrystalPilot SANS Plan", title="Strategy Name")
    plan_file: str = Field(default="", title="Strategy File", description="File path to the strategy CSV.")
    wait_for_list: List[str] = Field(default=["PCharge", "seconds"])

    # Row-edit dialog state (mirrors AnglePlanModel's edit affordances).
    is_editing_run: bool = Field(default=False, title="Is Editing")
    runedit_dialog: bool = Field(default=False, title="Run Edit Dialog")
    run_record: Dict = Field(default_factory=lambda: _default_run_record())

    def get_default_run_record(self) -> Dict:
        return _default_run_record()

    def load_strategy(self, file_path: str) -> None:
        """Read a SANS strategy CSV into ``strategy_list`` (and the raw copy).

        Strategy-row-shaped rows with SANS columns. Reads every row into the raw list,
        then normalises into canonical id-bearing dicts. Column names are
        provisional (TBD with SANS scientist).
        """
        with open(file_path, mode="r", newline="") as f:
            reader = csv.DictReader(f)
            self.strategy_list_read = list(reader)
        self._convert_read_to_strategy_list()

    def _convert_read_to_strategy_list(self) -> None:
        def _to_float(v: Any) -> float:
            if v in ("", None):
                return 0.0
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        new_list: List[Dict] = []
        for i, row in enumerate(self.strategy_list_read):
            new_row: Dict = {
                "id": i + 1,
                "title": row.get("Title", row.get("title", "")),
                "comment": row.get("Comment", row.get("comment", "")),
                "wait_for": row.get("Wait For", row.get("wait_for", "PCharge")),
                "value": row.get("Value", row.get("value", "")),
                "or_time": row.get("Or Time", row.get("or_time", "")),
            }
            for col in SANS_PARAM_COLUMNS:
                new_row[col] = _to_float(row.get(col))
            new_list.append(new_row)
        self.strategy_list = new_list

    def export_to_csv(self, file_path: str) -> str:
        """Write the canonical strategy list back out as a strategy-shaped CSV.

        Column layout: ``Title``, SANS parameter columns, ``Comment``,
        ``Wait For``, ``Value``. Column names provisional (TBD with SANS
        scientist). Returns the path written.
        """
        fieldnames = ["Title", *SANS_PARAM_COLUMNS, "Comment", "Wait For", "Value"]
        with open(file_path, mode="w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.strategy_list:
                out: Dict = {
                    "Title": row.get("title", "CrystalPilot"),
                    "Comment": row.get("comment", ""),
                    "Wait For": row.get("wait_for", "PCharge"),
                    "Value": row.get("value", 10),
                }
                for col in SANS_PARAM_COLUMNS:
                    out[col] = row.get(col, 0)
                writer.writerow(out)
        return file_path


def _default_run_record() -> Dict:
    record: Dict = {"id": 0, "title": "", "comment": ""}
    for col in SANS_PARAM_COLUMNS:
        record[col] = 0.0
    record.update({"wait_for": "PCharge", "value": 0, "or_time": ""})
    return record
