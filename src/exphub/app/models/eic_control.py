from pydantic import BaseModel, Field

from typing import List, Dict
import csv

from .EICClient import EICClient


class EICControlModel(BaseModel):

    class Config:
        arbitrary_types_allowed = True  # Allow arbitrary types like EICClient

    username: str = Field(
    default="test_name",
        min_length=1,
        title="User Name",
        description="Please provide the name of the user",
        examples=["user"],
    )
    token: str = Field(default="test_password", title="IPTS token")
    #token_file: str = Field(default="/home/zx5/1-todo/6-hardware/code/token.txt", title="IPTS token")
    #token_file: str = Field(default="/path/token.txt", title="IPTS token")
    token_file: str = Field(default="/SNS/TOPAZ/IPTS-34069/shared/token.txt", title="IPTS token")
    #token_file: str = Field(default="/SNS/TOPAZ/IPTS-35036/shared/token.txt", title="IPTS token")
    
    is_simulation: bool = Field(default=True, title="Simulation")
    IPTS_number: str = Field(default="35036", title="IPTS number")
    instrument_name: str = Field(default="TOPAZ", title="Instrument name", description="Name of the instrument",
                                 type="select", items=["TOPAZ", "CORELLI", "SEQUOIA", "HYSPEC", "ARCS", "VISION"])
    beamline: str = Field(default="bl12", title="Beamline", description="Name of the beamline")
    #eic_client: EICClient = Field(default_factory=EICClient, title="EIC Client")
    #eic_client: EICClient = Field(default_factory=EICClient, title="EIC Client")
    beamline_database: Dict = Field(default={
                                     "TOPAZ": "bl12",
                                     "CORELLI": "bl9"}
                                     , title="Beamline Database")

    eic_submission_success: List[bool] = Field(default=[False], title="EIC Submission Success")
    eic_submission_message: List[str] = Field(default=["No message"], title="EIC Submission Message")
    eic_submission_scan_id: int = Field(default=-1, title="EIC Submission Scan ID")
    eic_submission_status: str = Field(default="No status", title="EIC Submission Status")

    eic_auto_stop_strategy: str=Field(default="By Uncertainty", title="Auto Steering Strategy")
    eic_auto_stop_strategy_options: List[str]=Field(default=["By Uncertainty","By SNR","No Auto Stop"], title="EIC Auto Stop Strategy")
    eic_auto_stop_uncertainty_threshold: float=Field(default=0.1, title="Threshold")
    eic_auto_stop_snr_threshold: float=Field(default=10.0, title="Threshold SNR")

    eic_submission_scan_id_list: List[int] = Field(default=[-1], title="EIC Submission Scan ID List")
    current_scan_idx: int = Field(default=0, title="Current Scan Index")


    def load_token(self, file_path: str) -> None:
        with open(file_path, mode='r') as tokenfile:
            self.token = tokenfile.read()
            print(self.token)
    def submit_eic(self,angleplan:List[Dict]) -> None:
        # Implement the submit logic here
        self.beamline = self.beamline_database[self.instrument_name]
        eic_client = EICClient(self.token, beamline=self.beamline, ipts_number=self.IPTS_number)
        eic_client.is_eic_enabled(print_results=True)

        desc="CrystalPilot Submission"
        if self.beamline == "bl12":
            headers=['Title','Comment','BL12:Mot:goniokm:phi','BL12:Mot:goniokm:omega','Wait For','Value','Or Time']
        rows=[[angle[key] for key in headers] for angle in angleplan]

        self.eic_submission_success= []
        self.eic_submission_message= []
        self.eic_submission_scan_id_list= []
        for row  in rows:
            print(row)
            desc_sub=desc+" "+row[0]
            success, scan_id, response_data = eic_client.submit_table_scan( 
                parms={'run_mode': 0, 'headers': headers, 'rows': [row]}, desc=desc_sub, simulate_only=self.is_simulation)
            parms={'run_mode': 0, 'headers': headers, 'rows': rows}
            print(parms)
            print(success, scan_id, response_data)
            self.eic_submission_success.append(success)
            self.eic_submission_message.append(response_data['eic_response_message'])
            self.eic_submission_scan_id_list.append(scan_id)
        self.current_scan_idx=0
        self.eic_submission_scan_id=self.eic_submission_scan_id_list[self.current_scan_idx]

        #self.eic_submission_status=eic_client.get_scan_status(scan_id=scan_id)
        #print(self.eic_submission_status)
    def stop_run(self) -> None:
        # Implement the stop logic here
        self.beamline = self.beamline_database[self.instrument_name]
        eic_client = EICClient(self.token, beamline=self.beamline, ipts_number=self.IPTS_number)
        eic_client.is_eic_enabled(print_results=True)
        #if self.scan_id
        print(self.eic_submission_scan_id)
        print(self.eic_submission_scan_id_list)
        eic_client.abort_scan(scan_id=self.eic_submission_scan_id_list[self.current_scan_idx])
        self.current_scan_idx+=1
        self.eic_submission_scan_id=self.eic_submission_scan_id_list[self.current_scan_idx]
        

        pass