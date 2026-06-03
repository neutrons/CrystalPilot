"""Single-crystal EIC row builder.

Translates a single-crystal angle plan into the per-row EIC table-scan
submission payloads (``headers`` + ``row``) plus the display metadata the
EIC Control panel shows for each submitted job.

This is the single-crystal half of the EIC seam introduced in P3a: the
framework-agnostic submit/poll/abort plumbing lives in
``exphub.core.eic.control``; the single-crystal CSV column layout
(goniometer angle columns, ramp PV columns, run-title PV) lives here.

P3a.2 will formalize this as an ``EICRowBuilder`` protocol declared on the
``TechniqueManifest``; for now it is a module-level helper called directly
by the single-crystal steering view-model. The CSV/row shape is identical
to the pre-refactor ``EICControlModel`` so single-crystal submission
behavior is unchanged for every single-crystal beamline.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Any, Dict, List

from ....core.beamline import active as _active_beamline
from ....core.paths import resolver_for as _resolver_for
from ..models import gonio_pvs


def write_strategy_csv(
    angleplan: List[Dict],
    ipts_number: str,
    goniometer_type: str = gonio_pvs.AMBIENT,
) -> str:
    """Write the experiment-strategy CSV to the EIC dropbox location.

    Column layout depends on ``goniometer_type``; ramp rows fill the ramp PV
    columns and leave Wait For/Value blank. Returns the destination path.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    filename = f"CrystalPilot-experiment-plan-{timestamp}.csv"
    destination_dir = _resolver_for(ipts_number).eic_dropbox
    destination_path = os.path.join(destination_dir, filename)

    try:
        os.makedirs(destination_dir, exist_ok=True)
        print(f"Ensured directory exists: {destination_dir}")
    except OSError as e:
        print(f"Failed to create directory {destination_dir}: {e}")
        raise

    run_title_pv = _active_beamline().single_crystal.run_title_pv
    angle_cols = gonio_pvs.angle_columns(goniometer_type)
    ramp_cols = list(gonio_pvs.RAMP_PVS.values())
    fieldnames = [
        run_title_pv,
        *angle_cols,
        *ramp_cols,
        "Comment",
        "Wait For",
        "Value",
    ]
    pvs = gonio_pvs.ANGLE_PVS[goniometer_type]
    with open(destination_path, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for angle in angleplan:
            row: Dict = {
                run_title_pv: angle.get("title", "CrystalPilot"),
                "Comment": angle.get("comment", ""),
                pvs["omega"]: angle.get("omega", 0),
            }
            if "phi" in pvs:
                row[pvs["phi"]] = angle.get("phi", 0)

            if angle.get("step_type") == "ramp":
                row[gonio_pvs.RAMP_PVS["start"]] = angle.get("ramp_start", "")
                row[gonio_pvs.RAMP_PVS["end"]] = angle.get("ramp_end", "")
                row[gonio_pvs.RAMP_PVS["rate"]] = angle.get("ramp_rate", "")
                row[gonio_pvs.RAMP_PVS["soak"]] = angle.get("ramp_soak", "")
                row[gonio_pvs.RAMP_PVS["run"]] = angle.get("ramp_run", "")
                row["Wait For"] = ""
                row["Value"] = ""
            else:
                wait_for = angle.get("wait_for", "PCharge")
                row["Wait For"] = (
                    gonio_pvs.WAIT_FOR_PCHARGE_PV if wait_for == "PCharge" else wait_for
                )
                row["Value"] = angle.get("value", 10)
            writer.writerow(row)
    print(f"Copied experiment strategy to {destination_path}")
    return destination_path


def build_jobs(
    angleplan: List[Dict],
    goniometer_type: str = gonio_pvs.AMBIENT,
) -> List[Dict[str, Any]]:
    """Build the per-row EIC submission payloads for a single-crystal plan.

    Returns one job dict per angle-plan entry. Each dict carries the EIC
    table-scan ``headers`` + ``row`` to submit plus the display metadata the
    EIC Control panel renders (``title``/``phi``/``omega``). Angle and ramp
    rows can carry different column layouts, so headers travel per-row.
    """
    pvs = gonio_pvs.ANGLE_PVS[goniometer_type]

    angle_headers = ["Title", "Comment", pvs["omega"]]
    angle_keys: List[str] = ["title", "comment", "omega"]
    if "phi" in pvs:
        angle_headers.append(pvs["phi"])
        angle_keys.append("phi")
    angle_headers.extend(["Wait For", "Value"])
    angle_keys.extend(["wait_for", "value"])

    ramp_headers = ["Title", "Comment", *gonio_pvs.RAMP_PVS.values()]
    ramp_keys = ["title", "comment", "ramp_start", "ramp_end", "ramp_rate", "ramp_soak", "ramp_run"]

    jobs: List[Dict[str, Any]] = []
    for angle in angleplan:
        if angle.get("step_type") == "ramp":
            headers = ramp_headers
            keys = ramp_keys
        else:
            headers = angle_headers
            keys = angle_keys

        def _cell(k: str, entry: Dict = angle) -> object:
            v = entry.get(k)
            if k == "wait_for" and v == "PCharge":
                return gonio_pvs.WAIT_FOR_PCHARGE_PV
            return "" if v is None else v

        row = [_cell(k) for k in keys]
        jobs.append(
            {
                "headers": headers,
                "row": row,
                "title": angle.get("title", ""),
                "phi": angle.get("phi", 0.0) or 0.0,
                "omega": angle.get("omega", 0.0) or 0.0,
            }
        )
    return jobs
