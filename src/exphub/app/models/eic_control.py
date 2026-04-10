"""Model for EIC Control."""

import csv
import os
from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field

from .eic_client import EICClient


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
    # token_file: str = Field(default="/SNS/TOPAZ/IPTS-35036/shared/token.txt", title="IPTS token")

    is_simulation: bool = Field(default=True, title="Simulation")
    beamline: str = Field(default="bl12", title="Beamline", description="Name of the beamline")
    # eic_client: EICClient = Field(default_factory=EICClient, title="EIC Client")
    # eic_client: EICClient = Field(default_factory=EICClient, title="EIC Client")
    beamline_database: Dict = Field(default={"TOPAZ": "bl12", "CORELLI": "bl9"}, title="Beamline Database")

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

    def _copy_strategy_to_eic(self, angleplan: List[Dict], ipts_number: str) -> str:
        """Copy the experiment strategy CSV to the EIC submission location.

        Returns the destination file path.
        """
        # Create timestamp in format: YYYY-MM-DD-HHMMSS
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        filename = f"CrystalPilot-experiment-plan-{timestamp}.csv"

        # Build destination path: /SNS/groups/topaz/bl_12/IPTS-xxxxx/
        destination_dir = f"/SNS/groups/topaz/bl_12/IPTS-{ipts_number}"
        destination_path = os.path.join(destination_dir, filename)

        # Create directory if it doesn't exist
        try:
            os.makedirs(destination_dir, exist_ok=True)
            print(f"Ensured directory exists: {destination_dir}")
        except OSError as e:
            print(f"Failed to create directory {destination_dir}: {e}")
            raise

        # Write CSV file at destination
        fieldnames = [
            "BL12:SMS:RunInfo:RunTitle",
            "BL12:Mot:goniokm:omega",
            "BL12:Mot:goniokm:chi",
            "BL12:Mot:goniokm:phi",
            "Comment",
            "Wait For",
            "Value",
        ]
        with open(destination_path, mode="w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for angle in angleplan:
                wait_for = angle.get("wait_for", "PCharge")
                # Map internal wait_for to EIC PV name
                if wait_for == "PCharge":
                    wait_for_pv = "BL12:Det:PCharge:C"
                else:
                    wait_for_pv = wait_for
                writer.writerow(
                    {
                        "BL12:SMS:RunInfo:RunTitle": angle.get("title", "CrystalPilot"),
                        "BL12:Mot:goniokm:omega": angle.get("omega", 0),
                        "BL12:Mot:goniokm:chi": angle.get("chi", 0),
                        "BL12:Mot:goniokm:phi": angle.get("phi", 0),
                        "Comment": angle.get("comment", ""),
                        "Wait For": wait_for_pv,
                        "Value": angle.get("value", 10),
                    }
                )
        print(f"Copied experiment strategy to {destination_path}")
        return destination_path

    def submit_eic(self, angleplan: List[Dict], ipts_number: str, instrument_name: str) -> None:
        # Copy strategy to EIC submission location first
        try:
            self._copy_strategy_to_eic(angleplan, ipts_number)
        except Exception as e:
            print(f"Warning: failed to copy strategy to EIC location: {e}")

        # Implement the submit logic here
        self.beamline = self.beamline_database[instrument_name]
        eic_client = EICClient(self.token, beamline=self.beamline, ipts_number=ipts_number)
        eic_client.is_eic_enabled(print_results=True)

        desc = "CrystalPilot Submission"
        if self.beamline == "bl12":
            eic_headers = [
                "Title",
                "Comment",
                "BL12:Mot:goniokm:phi",
                "BL12:Mot:goniokm:omega",
                "Wait For",
                "Value",
            ]
            angle_keys = ["title", "comment", "phi", "omega", "wait_for", "value"]
        else:
            self.supported_beamline = False

        rows = [[angle[key] for key in angle_keys] for angle in angleplan]

        self.eic_submission_success = []
        self.eic_submission_message = []
        self.eic_submission_scan_id_list = []
        self.submitted_jobs = []
        for idx, row in enumerate(rows):
            print(row)
            desc_sub = desc + " " + row[0]
            success, scan_id, response_data = eic_client.submit_table_scan(
                parms={"run_mode": 0, "headers": eic_headers, "rows": [row]},
                desc=desc_sub,
                simulate_only=self.is_simulation,
            )
            parms = {"run_mode": 0, "headers": eic_headers, "rows": rows}
            print(parms)
            print(success, scan_id, response_data)
            self.eic_submission_success.append(success)
            self.eic_submission_message.append(response_data["eic_response_message"])
            self.eic_submission_scan_id_list.append(scan_id)

            angle = angleplan[idx]
            job = SubmittedJob(
                index=idx + 1,
                title=angle.get("title", ""),
                scan_id=scan_id if scan_id is not None else -1,
                phi=angle.get("phi", 0.0),
                omega=angle.get("omega", 0.0),
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
