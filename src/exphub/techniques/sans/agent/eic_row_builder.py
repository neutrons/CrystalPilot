"""SANS EIC row builder (P4.3).

The SANS half of the EIC seam introduced in P3a (the single-crystal half is
:mod:`exphub.techniques.single_crystal.agent.eic_row_builder`). The
framework-agnostic submit/poll/abort plumbing lives in
:mod:`exphub.core.eic.control`; the per-technique CSV column layout lives here.

Column shape (per ``MULTI_TECHNIQUE_PLAN.md`` DECISION DEFAULTS):
single-crystal-shaped rows — ``Title``, ``Comment``, ``Wait For``, ``Value`` —
but the goniometer angle columns are replaced with the SANS
instrument-configuration placeholders
from :data:`~exphub.techniques.sans.models.strategy.SANS_PARAM_COLUMNS`
(``sample_aperture`` / ``detector_distance`` / ``attenuator`` /
``wavelength_spread``). **Column names are provisional — TBD with the SANS
scientist.**

SANS plans are homogeneous (no ramp-vs-angle row split as in single crystal),
so every job shares one header layout; :meth:`build_rows` is therefore the
natural flat form and :meth:`build_jobs` simply wraps it per-row. Wired onto the
SANS manifest as :data:`SANS_EIC_ROW_BUILDER`; the SANS steering VM resolves it
via ``active_technique().eic_row_builder`` on submit.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

from ....core.paths import resolver_for as _resolver_for
from ..models.strategy import SANS_PARAM_COLUMNS

# EIC table-scan header order for a SANS row. Single-crystal-shaped tail
# (Title/Comment ... Wait For/Value) with the goniometer angle columns replaced
# by the SANS instrument-configuration placeholders. column names provisional
# (TBD with SANS scientist).
_SANS_HEADERS: List[str] = ["Title", "Comment", *SANS_PARAM_COLUMNS, "Wait For", "Value"]
# Matching strategy-row dict keys, same order as the headers above.
_SANS_KEYS: List[str] = ["title", "comment", *SANS_PARAM_COLUMNS, "wait_for", "value"]


class SansEICRowBuilder:
    """``EICRowBuilder`` for SANS instrument-configuration strategy tables.

    Stateless: one shared instance serves every SANS beamline. The CSV column
    layout is provisional (TBD with the SANS scientist).
    """

    def write_strategy_csv(
        self,
        strategy_rows: List[Dict],
        ipts_number: str,
        *_args: Any,
        **_kwargs: Any,
    ) -> str:
        """Write the SANS strategy CSV to the EIC dropbox location.

        Columns: ``Title``, the SANS parameter columns, ``Comment``,
        ``Wait For``, ``Value`` (column names provisional, TBD with SANS
        scientist). Returns the destination path.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        filename = f"CrystalPilot-sans-plan-{timestamp}.csv"
        destination_dir = _resolver_for(ipts_number).eic_dropbox
        destination_path = os.path.join(destination_dir, filename)

        try:
            os.makedirs(destination_dir, exist_ok=True)
            print(f"Ensured directory exists: {destination_dir}")
        except OSError as e:
            print(f"Failed to create directory {destination_dir}: {e}")
            raise

        fieldnames = ["Title", *SANS_PARAM_COLUMNS, "Comment", "Wait For", "Value"]
        with open(destination_path, mode="w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in strategy_rows:
                out: Dict = {
                    "Title": row.get("title", "CrystalPilot"),
                    "Comment": row.get("comment", ""),
                    "Wait For": row.get("wait_for", "PCharge"),
                    "Value": row.get("value", 10),
                }
                for col in SANS_PARAM_COLUMNS:
                    out[col] = row.get(col, 0)
                writer.writerow(out)
        print(f"Copied SANS strategy to {destination_path}")
        return destination_path

    def build_rows(
        self,
        strategy_rows: List[Dict],
        ipts: str = "",
        spec: Any = None,
        **_kwargs: Any,
    ) -> Tuple[List[str], List[List[Any]]]:
        """Return ``(headers, rows)`` for the SANS strategy plan.

        SANS plans are homogeneous, so a single shared header layout always
        applies. Returns the SANS header order and one flat value row per
        strategy step.
        """
        rows: List[List[Any]] = []
        for entry in strategy_rows:
            rows.append([_cell(entry, k) for k in _SANS_KEYS])
        return list(_SANS_HEADERS), rows

    def build_jobs(
        self,
        strategy_rows: List[Dict],
        **_kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Build the per-row EIC submission payloads for a SANS plan.

        Returns one job dict per strategy step. Each carries the EIC table-scan
        ``headers`` + ``row`` to submit plus the display metadata the EIC
        Control panel renders. SANS has no goniometer, so ``phi`` / ``omega``
        are omitted (only ``title`` travels as display metadata).
        """
        headers, rows = self.build_rows(strategy_rows)
        jobs: List[Dict[str, Any]] = []
        for entry, row in zip(strategy_rows, rows, strict=True):
            jobs.append(
                {
                    "headers": headers,
                    "row": row,
                    "title": entry.get("title", ""),
                }
            )
        return jobs


def _cell(entry: Dict, key: str) -> object:
    v = entry.get(key)
    return "" if v is None else v


# Shared stateless instance wired onto the SANS manifest's ``eic_row_builder``
# field; the SANS submit path resolves it via
# ``active_technique().eic_row_builder``.
SANS_EIC_ROW_BUILDER = SansEICRowBuilder()
