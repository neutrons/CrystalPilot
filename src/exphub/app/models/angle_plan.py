from pydantic import BaseModel, Field, computed_field, field_validator, model_validator
from typing import List, Dict
import csv


class RunPlan(BaseModel):
    title: str =Field(default="Untitled")
    comment: str = Field(default="")
    phi: float = Field(default=0.0)
    omega: float = Field(default=0.0)
    wait_for: str = Field(default="")
    value: float = Field(default=0.0)
    or_time: float = Field(default=0.0)

class AnglePlanModel(BaseModel):

    #headers: List[str] = Field(default=["Title", "Comment", "phi", "omega", "Wait For", "Value", "Or Time"])
    #headers: List[str] = Field(default=["Title", "Comment", "BL12:Mot:goniokm:phi", "BL12:Mot:goniokm:omega", "Wait For", "Value", "Or Time"])
    angle_keys: List[str]=Field(default=['id','title','comment','chi','phi','omega','wait_for','value','or_time'])
    angle_list_headers: List[Dict] = Field(default=[
        {"title":  "Title"    ,"value":"title"   ,"sortable":True , "align":"center"},
        {"title":  "Comment"  ,"value":"comment" ,"sortable":True , "align":"center"},
#        {"title":  "chi"      ,"value":"chi"     ,"sortable":True , "align":"center"},
        {"title":  "phi"      ,"value":"phi"     ,"sortable":True , "align":"center"},
        {"title":  "omega"    ,"value":"omega"   ,"sortable":True , "align":"center"},
        {"title":  "Wait For" ,"value":"wait_for","sortable":True , "align":"center"},
        {"title":  "Value"    ,"value":"value"   ,"sortable":True , "align":"center"},
        {"title":  "Or Time"  ,"value":"or_time" ,"sortable":True , "align":"center"},
        {"title":  "Action"   ,"value":"actions" ,"sortable":False, "align":"center"},
        ])
    show_coverage: bool = Field(default=False, title="Show Coverage", description="Flag to indicate if coverage is shown")

    #table_test: List[Dict] = Field(default=[{"title":"1","header":"h"}])
    #test: str = Field(default="test", title="Test", description="Test field")
    #test_list: List[str] = Field(default=["test1", "test2"])
    #test_dict: List[Dict] = Field(default=[{"key1": "testdict1", "key2": "testdict2"}])
    #test_dict: List[List] = Field(default=[[ "testlist1"],[  "testlist2"]])

    ###########################################################################################################################################
    #TODO: pydantic model variable realization for angle list: used for pydnatic table(vrow)
    #run_plan1=RunPlan(title="test_angleplan_1",comment="",phi=0,omega=0,wait_for="PCharge",value=10,or_time=0)
    #run_plan2=RunPlan(title="test_angleplan_2",comment="",phi=10,omega=10,wait_for="PCharge",value=10,or_time=0)
    #angle_list_pd:List[RunPlan]=Field(default=[run_plan1,run_plan2])
    angle_list_pd:List[RunPlan]=Field(default=[
               RunPlan(title="test_angleplan_1",comment="",phi=0,omega=0,wait_for="PCharge",value=10,or_time=0),
               RunPlan(title="test_angleplan_2",comment="",phi=10,omega=10,wait_for="PCharge",value=10,or_time=0)
    ])
    ###########################################################################################################################################

    is_editing_run: bool = Field(default=False, title="Is Editing", description="Flag to indicate if the angle plan is being edited")
    run_record:Dict = Field(default={"id":0,
                                     "title": "title",
                                    "comment": "",
                                    'chi': 0,
                                    "phi": 0,
                                    "omega": 0,
                                    "wait_for": "PCharge",
                                    "value": 0,
                                    "or_time": ""}, title="Run Record", description="Record of the run plan")
    runedit_dialog: bool = Field(default=False, title="Run Edit Dialog", description="Flag to indicate if the run edit dialog is open")

    angle_list_read:List[Dict] = Field(default=[
                                            {"Title":"",
                                             "Comment":"",
                                             "BL12:Mot:goniokm:phi":10,
                                             "BL12:Mot:goniokm:omega":10,
                                             "Wait For":"PCharge",
                                             "Value":10,
                                             "Or Time":""}
                                                ],
                                    title="Angle Plan",
                                    description="List of angles to be measured",)
    ##############################################################################
    angle_list: List[Dict] = Field(default=[{"id":1,
                                             "title":"test_angleplan_1",
                                             "comment":"",
                                             "chi":0,
                                             "phi":0,
                                             "omega":0,
                                             "wait_for": "PCharge",
                                             "value": 1,
                                             "or_time": ""},
                                            {"id":2,
                                             "title":"test_angleplan_2",
                                             "comment":"",
                                             "chi":10,
                                             "phi":10,
                                             "omega":10,
                                             "wait_for": "PCharge",
                                             "value": 1,
                                             "or_time": ""},
                                             ],
                                    title="Angle Plan",
                                    description="List of angles to be measured",)


    plan_name: str = Field(default="CrystalPilot Plan", title="Strategy Name", description="Name of the plan")

    plan_file: str = Field(default="/SNS/TOPAZ/IPTS-34069/shared/strategy.csv", title="Strategy File", description="File path to the plan file")
    #plan_file: str = Field(default="/SNS/TOPAZ/IPTS-35036/shared/strategy.csv", title="Strategy File", description="File path to the plan file")
    #plan_file: str = Field(default="/path/strategy.csv", title="Strategy File", description="File path to the plan file")
    #plan_file: str = Field(default="/home/zx5/1-todo/6-hardware/code/table.csv", title="Strategy File", description="File path to the plan file")
    plan_type: str = Field(default="Crystal Plan", title="Strategy Type", description="Type of the plan")
    plan_type_list: List[str] = Field(default=["CrystalPlan", "NeuXstalViz"])
    
    def get_default_run_record(self) -> Dict:
        return {
                "id":0,
                "title":"",
                "comment":"",
                "chi":0,
                "phi":0,
                "omega":0,
                "wait_for": "PCharge",
                "value": 0,
                "or_time": ""}

    #@field_validator("angle_list", mode="before")
    def load_ap(self, file_path: str) -> None:
        print("load_ap")
        with open(file_path, mode='r') as apfile:
            reader = csv.DictReader(apfile)
            self.angle_list_read = list(reader)
        self.convert_plan_format(self.plan_type,self.angle_list_read)
        self.convert_angle_list_read_to_angle_list()
        
        
        #print(self.angle_list)

    def convert_plan_format(self,source_type:str,angle_list:List[Dict]) -> None:
        if source_type == "Crystal Plan":
            new_angle_list = []
            for angle in angle_list:
                print(angle.keys())
                new_angle={}
                new_angle["Title"] = angle["Notes"]
                new_angle["Comment"] = ""
                new_angle["BL12:Mot:goniokm:phi"] = angle["BL12:Mot:goniokm:phi"]
                new_angle["BL12:Mot:goniokm:omega"] = angle["BL12:Mot:goniokm:omega"]
                wait_for_key = next((key for key in angle.keys() if key.startswith("Wait For")), None)
                if wait_for_key:
                    new_angle["Wait For"] = angle[wait_for_key]
                #new_angle["Wait For"] = angle["Wait For/n"]
                if "PCharge" in new_angle["Wait For"]:
                    new_angle["Wait For"] = "PCharge"
                new_angle["Value"] = angle["Value"]
                new_angle["Or Time"] = ""
                new_angle_list.append(new_angle)
            
        elif source_type == "NeuXstalViz":
            for angle in angle_list:
                angle["Title"] = angle["Title"].replace("_"," ")
                angle["Comment"] = angle["Comment"].replace("_"," ")
                angle["BL12:Mot:goniokm:phi"] = angle["BL12:Mot:goniokm:phi"]
                angle["BL12:Mot:goniokm:omega"] = angle["BL12:Mot:goniokm:omega"]
                angle["Wait For"] = angle["Wait For"].replace("_"," ")
                angle["Value"] = angle["Value"]
                angle["Or Time"] = angle["Or Time"].replace("_"," ")
        self.angle_list_read = new_angle_list
        pass
    def convert_angle_list_read_to_angle_list(self) -> None:
        if self.plan_type == "Crystal Plan":
            new_angle_list = []
            for i in range(len(self.angle_list_read)):
                angle=self.angle_list_read[i]
                new_angle={}
                new_angle["id"] = i+1
                new_angle["title"] = angle["Title"]
                new_angle["comment"] = angle["Comment"]
                new_angle["chi"] = 0
                new_angle["phi"] = angle["BL12:Mot:goniokm:phi"]
                new_angle["omega"] = angle["BL12:Mot:goniokm:omega"]
                new_angle["wait_for"] = angle["Wait For"]
                new_angle["value"] = angle["Value"]
                new_angle["or_time"] = angle["Or Time"]
                new_angle_list.append(new_angle)
        self.angle_list = new_angle_list
        pass

#    @model_validator(mode="after")
#    def validate_angle_list(self) -> bool:
#        if isinstance(self.angle_list,list):
#            for angle in self.angle_list:
#                if not isinstance(angle, dict):
#                    return False
#                if len(angle) not in [5, 7]:
#                    return False
#            return True
#        else:
#            return False

    def submit_to_eic(self) -> None:
        # Implement the submit logic here
        pass