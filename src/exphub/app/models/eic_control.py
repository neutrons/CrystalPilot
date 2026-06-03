"""Model for EIC Control."""

import csv
import os
from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field

from ...core.beamline import active as _active_beamline
from ...core.beamline import get as _get_beamline
from ...core.beamline import list_ids as _beamline_ids
from ...core.paths import resolver_for as _resolver_for
from ...techniques.single_crystal.models import gonio_pvs
from .eic_client import EICClient


def _default_beamline_code() -> str:
    try:
        return _active_beamline().eic.beamline_code
    except Exception:
        return ""


def _default_beamline_database() -> Dict[str, str]:
    """Instrument name (Mantid) → EIC beamline code, from every registered beamline."""
    try:
        return {
            _get_beamline(bid).single_crystal.mantid.instrument_name: _get_beamline(bid).eic.beamline_code
            for bid in _beamline_ids()
            if _get_beamline(bid).single_crystal.mantid.instrument_name
        }
    except Exception:
        return {}


class SubmittedJob(BaseModel):
    """A single submitted EIC job."""

    index: int = 0
    title: str = ""
    scan_id: int = -1
    phi: float = 0.0
    omega: float = 0.0
    status: str = "pending"
    is_done: bool = False
    message: str = ""


class EICControlModel(BaseModel):
    """Model for EIC Control."""

    class Config:
        """Pydantic config options."""

        arbitrary_types_allowed = True  # Allow arbitrary types like EICClient

    username: str = Field(
        default="test_name",
        min_length=1,
        title="User Name",
        description="Please provide the name of the user",
        examples=["user"],
    )
    token: str = Field(default="test_password", title="IPTS token")
    # token_file: str = Field(default="/home/zx5/1-todo/6-hardware/code/token.txt", title="IPTS token")
    # token_file: str = Field(default="/path/token.txt", title="IPTS token")
    token_file: str = Field(default="", title="IPTS token")

    is_simulation: bool = Field(default=True, title="Simulation")
    beamline: str = Field(
        default_factory=_default_beamline_code,
        title="Beamline",
        description="Name of the beamline",
    )
    beamline_database: Dict = Field(
        default_factory=_default_beamline_database,
        title="Beamline Database",
    )

    eic_submission_success: List[bool] = Field(default=[False], title="EIC Submission Success")
    eic_submission_message: List[str] = Field(default=["No message"], title="EIC Submission Message")
    eic_submission_scan_id: int = Field(default=-1, title="EIC Submission Scan ID")
    eic_submission_status: str = Field(default="No status", title="EIC Submission Status")
    eic_status: str = Field(default="not authenticated", title="EIC Status")

    eic_auto_stop_strategy: str = Field(default="By Uncertainty", title="Auto Steering Strategy")
    eic_auto_stop_strategy_options: List[str] = Field(
        default=["By Uncertainty", "By SNR", "No Auto Stop"], title="EIC Auto Stop Strategy"
    )
    eic_auto_stop_uncertainty_threshold: float = Field(default=0.1, title="Threshold")
    eic_auto_stop_snr_threshold: float = Field(default=10.0, title="Threshold SNR")

    eic_submission_scan_id_list: List[int] = Field(default=[-1], title="EIC Submission Scan ID List")
    current_scan_idx: int = Field(default=0, title="Current Scan Index")

    correct_run_format: bool = Field(default=True, title="Correct Run Format")
    supported_beamline: bool = Field(default=True, title="Supported Beamline")

    submitted_jobs: List[Dict] = Field(default=[], title="Submitted Jobs")
    submitted_jobs_headers: List[Dict] = Field(
        default=[
            {"title": "#", "key": "index", "sortable": False, "width": "50px"},
            {"title": "Title", "key": "title", "sortable": False},
            {"title": "Scan ID", "key": "scan_id", "sortable": False},
            {"title": "Phi", "key": "phi", "sortable": False},
            {"title": "Omega", "key": "omega", "sortable": False},
            {"title": "Status", "key": "status", "sortable": False},
            {"title": "Message", "key": "message", "sortable": False},
            {"title": "Actions", "key": "actions", "sortable": False},
        ],
        title="Submitted Jobs Headers",
    )

    def load_token(self, file_path: str) -> None:
        with open(file_path, mode="r") as tokenfile:
            self.token = tokenfile.read()
            print(self.token)

    def _copy_strategy_to_eic(
        self,
        angleplan: List[Dict],
        ipts_number: str,
        goniometer_type: str = gonio_pvs.AMBIENT,
    ) -> str:
        """Copy the experiment strategy CSV to the EIC submission location.

        Column layout depends on goniometer_type; ramp rows fill the ramp PV
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

    def submit_eic(
        self,
        angleplan: List[Dict],
        ipts_number: str,
        instrument_name: str,
        goniometer_type: str = gonio_pvs.AMBIENT,
    ) -> None:
        try:
            self._copy_strategy_to_eic(angleplan, ipts_number, goniometer_type)
        except Exception as e:
            print(f"Warning: failed to copy strategy to EIC location: {e}")

        self.beamline = self.beamline_database.get(instrument_name, "")
        if not self.beamline:
            print(f"Instrument {instrument_name!r} is not a registered beamline; aborting EIC submit.")
            self.supported_beamline = False
            return
        eic_client = EICClient(self.token, beamline=self.beamline, ipts_number=ipts_number)
        eic_client.is_eic_enabled(print_results=True)

        desc = "CrystalPilot Submission"
        pvs = gonio_pvs.ANGLE_PVS[goniometer_type]
        # Per-step-type headers + key mappings. Each row is submitted on its own,
        # so angle and ramp rows can carry different column layouts.
        angle_headers = ["Title", "Comment", pvs["omega"]]
        angle_keys: List[str] = ["title", "comment", "omega"]
        if "phi" in pvs:
            angle_headers.append(pvs["phi"])
            angle_keys.append("phi")
        angle_headers.extend(["Wait For", "Value"])
        angle_keys.extend(["wait_for", "value"])

        ramp_headers = ["Title", "Comment", *gonio_pvs.RAMP_PVS.values()]
        ramp_keys = ["title", "comment", "ramp_start", "ramp_end", "ramp_rate", "ramp_soak", "ramp_run"]

        self.eic_submission_success = []
        self.eic_submission_message = []
        self.eic_submission_scan_id_list = []
        self.submitted_jobs = []
        for idx, angle in enumerate(angleplan):
            if angle.get("step_type") == "ramp":
                headers = ramp_headers
                keys = ramp_keys
            else:
                headers = angle_headers
                keys = angle_keys

            def _cell(k: str) -> object:
                v = angle.get(k)
                if k == "wait_for" and v == "PCharge":
                    return gonio_pvs.WAIT_FOR_PCHARGE_PV
                return "" if v is None else v

            row = [_cell(k) for k in keys]
            print(row)
            desc_sub = desc + " " + str(row[0])
            success, scan_id, response_data = eic_client.submit_table_scan(
                parms={"run_mode": 0, "headers": headers, "rows": [row]},
                desc=desc_sub,
                simulate_only=self.is_simulation,
            )
            print({"run_mode": 0, "headers": headers, "rows": [row]})
            print(success, scan_id, response_data)
            self.eic_submission_success.append(success)
            self.eic_submission_message.append(response_data["eic_response_message"])
            self.eic_submission_scan_id_list.append(scan_id)

            job = SubmittedJob(
                index=idx + 1,
                title=angle.get("title", ""),
                scan_id=scan_id if scan_id is not None else -1,
                phi=angle.get("phi", 0.0) or 0.0,
                omega=angle.get("omega", 0.0) or 0.0,
                status="submitted" if success else "failed",
                is_done=False,
                message=response_data.get("eic_response_message", ""),
            )
            self.submitted_jobs.append(job.model_dump())
        self.current_scan_idx = 0
        self.eic_submission_scan_id = self.eic_submission_scan_id_list[self.current_scan_idx]

        # self.eic_submission_status=eic_client.get_scan_status(scan_id=scan_id)
        # print(self.eic_submission_status)

    def stop_run(self, ipts_number: str, instrument_name: str) -> None:
        # Implement the stop logic here
        self.beamline = self.beamline_database[instrument_name]
        eic_client = EICClient(self.token, beamline=self.beamline, ipts_number=ipts_number)
        eic_client.is_eic_enabled(print_results=True)
        # if self.scan_id
        print(self.eic_submission_scan_id)
        print(self.eic_submission_scan_id_list)
        # eic_client.abort_scan(scan_id=self.eic_submission_scan_id_list[self.current_scan_idx])
        eic_client.abort_scan(scan_id=self.eic_submission_scan_id)
        # self.current_scan_idx+=1
        # self.eic_submission_scan_id=self.eic_submission_scan_id_list[self.current_scan_idx]

    def poll_job_statuses(self, ipts_number: str, instrument_name: str) -> None:
        """Poll EIC for the current status of all submitted jobs."""
        if not self.submitted_jobs:
            return
        self.beamline = self.beamline_database[instrument_name]
        eic_client = EICClient(self.token, beamline=self.beamline, ipts_number=ipts_number)
        terminal_states = {"done", "aborted", "failed", "stopped"}
        for job in self.submitted_jobs:
            if job["status"] in terminal_states:
                continue
            scan_id = job["scan_id"]
            if scan_id < 0:
                continue
            try:
                success, is_done, state, response_data = eic_client.get_scan_status(scan_id=scan_id)
                if success and state is not None:
                    job["status"] = str(state).lower()
                    job["is_done"] = bool(is_done)
                elif not success:
                    job["status"] = "error"
                    job["message"] = response_data.get("eic_response_message", "status check failed")
            except Exception as e:
                job["status"] = "error"
                job["message"] = str(e)

    def abort_job(self, scan_id: int, ipts_number: str, instrument_name: str) -> None:
        """Abort a single job by scan_id."""
        self.beamline = self.beamline_database[instrument_name]
        eic_client = EICClient(self.token, beamline=self.beamline, ipts_number=ipts_number)
        try:
            eic_client.abort_scan(scan_id=scan_id)
            for job in self.submitted_jobs:
                if job["scan_id"] == scan_id:
                    job["status"] = "aborted"
                    job["is_done"] = True
        except Exception as e:
            for job in self.submitted_jobs:
                if job["scan_id"] == scan_id:
                    job["message"] = f"abort failed: {e}"
