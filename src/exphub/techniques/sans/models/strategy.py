"""SANS experiment-strategy model — flexible-column strategy table.

Unlike the single-crystal ``AnglePlanModel`` (which has a fixed goniometer-shaped
row), the SANS strategy table is **column-flexible**: a strategy CSV may carry an
arbitrary set of columns with arbitrary names and types. The only guaranteed
column is :data:`GROUP_KEY` (``BL1A:sampleholder``), an integer whose value
groups rows into **Samples** — every row sharing a holder value is one Sample's
measurement steps.

The table is discovered at upload time:

  - :meth:`SansStrategyModel.load_strategy` reads the CSV, preserves the column
    order into :attr:`~SansStrategyModel.columns`, builds a per-column
    :data:`ColumnSpec` list (:func:`build_column_specs`), keeps every cell value
    as a string (lossless round-trip), injects a stable ``id`` per row, and
    computes the Sample groups.
  - The view renders one expandable panel per Sample and edits cells inline
    (every column except the group key).
  - :meth:`export_to_csv` writes the edited table back out in the original
    column order.

Column typing (enum / number / string) is inferred from the data and/or supplied
by :data:`COLUMN_CATALOG` — the seam for the authoritative column description the
SANS scientist will provide later. Types drive validation
(:meth:`guidance_check`) and which inline editor the view shows; values
themselves are stored verbatim as strings.
"""

from __future__ import annotations

import csv
from typing import Any, Dict, List

from pydantic import BaseModel, Field

# The one column every SANS strategy CSV must contain. Its integer value groups
# rows into Samples. Not editable in the UI.
GROUP_KEY = "BL1A:sampleholder"

# ---------------------------------------------------------------------------
# Column description seam (request item 2 — "complete description added later").
#
# COLUMN_CATALOG maps a raw CSV header -> partial ColumnSpec overrides that WIN
# over inference. It is intentionally near-empty today; when the SANS scientist
# provides the authoritative column catalogue, add entries here, e.g.:
#
#   COLUMN_CATALOG = {
#       "Wait For": {"type": "enum",
#                    "options": ["seconds", "Counts", "PCharge"],
#                    "label": "Wait For"},
#       "BL1A:anlge": {"type": "float", "label": "Analyser angle", "required": True},
#   }
#
# Until then, everything is inferred from the data (see infer_column_spec).
# ---------------------------------------------------------------------------
COLUMN_CATALOG: Dict[str, Dict[str, Any]] = {}

# Columns whose name (case-insensitive) marks them as an enum, with the known
# control words. Observed values not in the list are appended so nothing a CSV
# actually contains is rejected by the dropdown. Extend as columns are specified.
_KNOWN_ENUMS: Dict[str, List[str]] = {
    "wait for": ["seconds", "Counts", "PCharge", "minutes", "hours"],
}

# A ColumnSpec is a plain dict (kept JSON-serialisable so it can cross the trame
# binding to the view). Shape:
#   {"key": str, "label": str, "type": "int"|"float"|"str"|"enum",
#    "options": List[str], "editable": bool, "required": bool}
ColumnSpec = Dict[str, Any]


def _looks_float(s: Any) -> bool:
    try:
        float(str(s))
        return True
    except (TypeError, ValueError):
        return False


def _looks_int(s: Any) -> bool:
    try:
        f = float(str(s))
        return f == int(f)
    except (TypeError, ValueError):
        return False


def infer_column_spec(name: str, values: List[Any]) -> ColumnSpec:
    """Infer a :data:`ColumnSpec` for a column from its name and sample values.

    The group key is always forced to an integer, non-editable, required column.
    A column named like a known enum becomes an enum; a column whose non-blank
    values are all numeric becomes ``int``/``float``; everything else is ``str``.
    """
    label = str(name)
    if name == GROUP_KEY:
        return {
            "key": name,
            "label": "Sample Holder",
            "type": "int",
            "options": [],
            "editable": False,
            "required": True,
        }

    nonblank = [str(v).strip() for v in values if str(v).strip() != ""]

    low = name.strip().lower()
    if low in _KNOWN_ENUMS:
        options: List[str] = list(_KNOWN_ENUMS[low])
        for v in nonblank:
            if v not in options:
                options.append(v)
        return {"key": name, "label": label, "type": "enum", "options": options, "editable": True, "required": False}

    if nonblank and all(_looks_float(v) for v in nonblank):
        col_type = "int" if all(_looks_int(v) for v in nonblank) else "float"
        return {"key": name, "label": label, "type": col_type, "options": [], "editable": True, "required": False}

    return {"key": name, "label": label, "type": "str", "options": [], "editable": True, "required": False}


def build_column_specs(columns: List[str], rows: List[Dict[str, Any]]) -> List[ColumnSpec]:
    """Build the per-column :data:`ColumnSpec` list (catalog overrides inference)."""
    specs: List[ColumnSpec] = []
    for name in columns:
        values = [r.get(name, "") for r in rows]
        spec = infer_column_spec(name, values)
        override = COLUMN_CATALOG.get(name)
        if override:
            spec = {**spec, **override, "key": name}
            spec.setdefault("label", name)
            spec.setdefault("options", [])
            spec.setdefault("editable", name != GROUP_KEY)
            spec.setdefault("required", name == GROUP_KEY)
        specs.append(spec)
    return specs


def _holder_sort_key(holder: Any) -> tuple[int, Any]:
    """Sort holders numerically when possible, else lexicographically."""
    try:
        return (0, int(float(str(holder))))
    except (TypeError, ValueError):
        return (1, str(holder))


class SansStrategyModel(BaseModel):
    """CSV-loadable, column-flexible SANS strategy table, grouped by Sample."""

    # The mandatory grouping column. Kept configurable so a future beamline whose
    # holder PV differs can override it, but defaults to the USANS holder PV.
    group_key: str = Field(default=GROUP_KEY, title="Group Key")

    # Raw CSV column order (excludes the injected ``id``). Drives export order and
    # the inline editor column order.
    columns: List[str] = Field(default_factory=list, title="Columns")
    # Per-column ColumnSpec dicts (see build_column_specs). Pushed to the view so
    # it knows each column's label / type / options / editability.
    column_specs: List[Dict] = Field(default_factory=list, title="Column Specs")

    # Canonical editable rows: string cell values keyed by raw column name, plus a
    # stable integer ``id``. This is the surface the inline editor writes to.
    strategy_list: List[Dict] = Field(
        default_factory=list,
        title="SANS Strategy",
        description="Flexible-column strategy rows (string cells + id), grouped by the sample-holder column.",
    )
    # Sample groups derived from strategy_list: one entry per distinct holder,
    # holder-sorted. Pushed to the view to render the expandable panels.
    groups: List[Dict] = Field(default_factory=list, title="Sample Groups")

    # Raw rows as read from the CSV, before id injection. Excluded from state pushes.
    strategy_list_read: List[Dict] = Field(
        default_factory=list,
        title="SANS Strategy (raw)",
        description="Rows as read from the uploaded CSV before normalisation.",
        exclude=True,
    )

    plan_name: str = Field(default="CrystalPilot SANS Plan", title="Strategy Name")
    plan_file: str = Field(default="", title="Strategy File", description="File path to the strategy CSV to upload.")
    export_file: str = Field(
        default="", title="Export File", description="Destination path for exporting the edited strategy CSV."
    )

    # Last pre-submission guidance result, pushed to the view for display.
    guidance_errors: List[str] = Field(default_factory=list, title="Guidance Errors")
    guidance_warnings: List[str] = Field(default_factory=list, title="Guidance Warnings")

    # ------------------------------------------------------------------ #
    # CSV load / export
    # ------------------------------------------------------------------ #
    def load_strategy(self, file_path: str) -> None:
        """Read a flexible-column SANS strategy CSV into ``strategy_list``.

        Preserves column order, skips fully blank lines, builds ``column_specs``,
        keeps every cell as a string, injects a stable ``id``, and recomputes the
        Sample groups.
        """
        with open(file_path, mode="r", newline="") as f:
            reader = csv.DictReader(f)
            columns = list(reader.fieldnames or [])
            raw_rows: List[Dict[str, Any]] = []
            for row in reader:
                if any(str(v or "").strip() for v in row.values()):
                    raw_rows.append({k: ("" if v is None else str(v)) for k, v in row.items() if k is not None})

        self.columns = columns
        self.strategy_list_read = [dict(r) for r in raw_rows]
        self.column_specs = build_column_specs(columns, raw_rows)

        new_list: List[Dict] = []
        for i, raw in enumerate(raw_rows):
            record: Dict[str, Any] = {"id": i + 1}
            for col in columns:
                record[col] = str(raw.get(col, "") or "")
            new_list.append(record)
        self.strategy_list = new_list
        self.recompute_groups()

    def export_to_csv(self, file_path: str) -> str:
        """Write the edited table back out in the original column order.

        The injected ``id`` is dropped; cell values are written verbatim, so a
        load → export round-trip is lossless (modulo the ``id``). Returns the
        path written.
        """
        fieldnames = list(self.columns)
        with open(file_path, mode="w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in self.strategy_list:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
        return file_path

    # ------------------------------------------------------------------ #
    # grouping + row editing helpers
    # ------------------------------------------------------------------ #
    def recompute_groups(self) -> None:
        """Rebuild ``groups`` (one per distinct holder value, holder-sorted)."""
        counts: Dict[str, int] = {}
        for row in self.strategy_list:
            holder = str(row.get(self.group_key, "")).strip()
            counts[holder] = counts.get(holder, 0) + 1
        ordered = sorted(counts, key=_holder_sort_key)
        self.groups = [
            {
                "holder": holder,
                "label": f"Sample {holder}" if holder != "" else "Sample (unassigned)",
                "count": counts[holder],
            }
            for holder in ordered
        ]

    def _next_id(self) -> int:
        return max((int(r.get("id", 0)) for r in self.strategy_list), default=0) + 1

    def _ensure_schema(self) -> None:
        """Seed a minimal schema (just the group key) if nothing is loaded yet."""
        if not self.columns:
            self.columns = [self.group_key]
            self.column_specs = build_column_specs(self.columns, [])

    def blank_row(self, holder: Any = "") -> Dict[str, Any]:
        """Build a new empty row for the current columns, holder pre-filled."""
        self._ensure_schema()
        record: Dict[str, Any] = {"id": self._next_id()}
        for col in self.columns:
            record[col] = str(holder) if col == self.group_key else ""
        return record

    def add_step(self, holder: Any) -> None:
        """Append a new empty step to the Sample identified by ``holder``."""
        self.strategy_list.append(self.blank_row(holder))
        self.recompute_groups()

    def add_sample(self) -> None:
        """Append a new Sample (next integer holder) with one empty step."""
        self._ensure_schema()
        existing: List[int] = []
        for row in self.strategy_list:
            try:
                existing.append(int(float(str(row.get(self.group_key, "")))))
            except (TypeError, ValueError):
                continue
        next_holder = (max(existing) + 1) if existing else 1
        self.strategy_list.append(self.blank_row(next_holder))
        self.recompute_groups()

    def remove_step(self, row_id: int) -> None:
        """Delete the step with the given id and recompute groups."""
        self.strategy_list = [r for r in self.strategy_list if int(r.get("id", -1)) != int(row_id)]
        self.recompute_groups()

    # ------------------------------------------------------------------ #
    # pre-submission guidance (request item 5 — real rules TBD)
    # ------------------------------------------------------------------ #
    def guidance_check(self) -> Dict[str, List[str]]:
        """Validate the table before EIC submission.

        Returns ``{"errors": [...], "warnings": [...]}``. Errors block submission;
        warnings are surfaced but allow it. The starter rules below cover
        structural integrity of the sample-holder grouping and per-column typing;
        real scientific guidance (allowed ranges, holder occupancy, exposure
        limits, …) is TBD with the SANS scientist and drops in where marked.
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not self.strategy_list:
            errors.append("Strategy table is empty — upload a CSV or add a Sample before submitting.")
        if self.columns and self.group_key not in self.columns:
            errors.append(f"Required column '{self.group_key}' is missing from the strategy.")

        for row in self.strategy_list:
            holder = str(row.get(self.group_key, "")).strip()
            rid = row.get("id")
            if holder == "":
                errors.append(f"Row {rid}: '{self.group_key}' is blank.")
            else:
                try:
                    int(float(holder))
                except (TypeError, ValueError):
                    errors.append(f"Row {rid}: '{self.group_key}' value '{holder}' is not an integer.")

        for spec in self.column_specs:
            if spec.get("required") and spec.get("key") not in self.columns:
                errors.append(f"Required column '{spec.get('key')}' is missing.")

        specs_by_key = {s.get("key"): s for s in self.column_specs}
        for row in self.strategy_list:
            rid = row.get("id")
            for key, spec in specs_by_key.items():
                if key == self.group_key:
                    continue
                value = str(row.get(key, "")).strip()
                if value == "":
                    continue
                col_type = spec.get("type")
                if col_type in ("int", "float") and not _looks_float(value):
                    warnings.append(f"Row {rid} column '{key}': '{value}' is not numeric.")
                elif col_type == "enum":
                    options = [str(o) for o in spec.get("options", [])]
                    if options and value not in options:
                        warnings.append(f"Row {rid} column '{key}': '{value}' is not one of {options}.")

        # ---- ADD SCIENTIFIC GUIDANCE RULES HERE (TBD with SANS scientist) ----

        return {"errors": errors, "warnings": warnings}

    def run_guidance(self) -> bool:
        """Run :meth:`guidance_check`, store the messages for display, return ok.

        ``True`` means no blocking errors (submission may proceed); warnings may
        still be present. The messages are stored on
        :attr:`guidance_errors` / :attr:`guidance_warnings` so the view can show
        them.
        """
        result = self.guidance_check()
        self.guidance_errors = result["errors"]
        self.guidance_warnings = result["warnings"]
        return not result["errors"]
