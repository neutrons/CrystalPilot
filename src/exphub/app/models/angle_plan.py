from pydantic import BaseModel, Field, computed_field, field_validator, model_validator
from typing import List, Dict
import csv


class AnglePlanModel(BaseModel):
    headers: List[str] = Field(default=["Title", "Comment", "phi", "omega", "Wait For", "Value", "Or Time"])
    #headers: List[str] = Field(default=["Title", "Comment", "BL12:Mot:goniokm:phi", "BL12:Mot:goniokm:omega", "Wait For", "Value", "Or Time"])
    table_test: List[Dict] = Field(default=[{"title":"1","header":"h"}])
    angle_list: List[Dict] = Field(default=[{"Title":"test_angleplan_1",
                                             "Comment":"",
                                             "BL12:Mot:goniokm:phi":0,
                                             "BL12:Mot:goniokm:omega":0,
                                             "Wait For":"PCharge",
                                             "Value":10,
                                             "Or Time":""},
                                             {"Title":"test_angleplan_2",
                                             "Comment":"",
                                             "BL12:Mot:goniokm:phi":0,
                                             "BL12:Mot:goniokm:omega":0,
                                             "Wait For":"PCharge",
                                             "Value":10,
                                             "Or Time":""}
                                             ],
                                    title="Angle Plan",
                                    description="List of angles to be measured",)



    test: str = Field(default="test", title="Test", description="Test field")
    test_list: List[str] = Field(default=["test1", "test2"])
    #test_dict: List[Dict] = Field(default=[{"key1": "testdict1", "key2": "testdict2"}])
    test_dict: List[List] = Field(default=[[ "testlist1"],[  "testlist2"]])
    plan_file: str = Field(default="/SNS/TOPAZ/IPTS-34069/shared/strategy.csv", title="Strategy File", description="File path to the plan file")
    #plan_file: str = Field(default="/SNS/TOPAZ/IPTS-35036/shared/strategy.csv", title="Strategy File", description="File path to the plan file")
    #plan_file: str = Field(default="/path/strategy.csv", title="Strategy File", description="File path to the plan file")
    #plan_file: str = Field(default="/home/zx5/1-todo/6-hardware/code/table.csv", title="Strategy File", description="File path to the plan file")
    
    plan_name: str = Field(default="test", title="Strategy Name", description="Name of the plan")
    plan_type: str = Field(default="Crystal Plan", title="Strategy Type", description="Type of the plan")
    data: List[Dict]= Field(default = [
        {"name": "John", "age": 25, "city": "New York"},
        {"name": "Jane", "age": 30, "city": "London"},
        {"name": "Alice", "age": 28, "city": "Paris"},
        {"name": "Bob", "age": 35, "city": "Berlin"}
    ])

    # Define columns for the data table
    #columns: List[Dict]= Field(default= [
    #    {"name": "name", "label": "Name", "align": "left"},
    #    {"name": "age", "label": "Age", "align": "center"},
    #    {"name": "city", "label": "City", "align": "center"}
    #])
    columns: List[Dict]= Field(default = [
        {"text": "Name", "value": "name"},
        {"text": "Age", "value": "age"},
        {"text": "City", "value": "city"}
    ])


    

    plan_type_list: List[str] = Field(default=["CrystalPlan", "NeuXstalViz"])
    def load_ap(self, file_path: str) -> None:
        print("load_ap")
        with open(file_path, mode='r') as apfile:
            reader = csv.DictReader(apfile)
            self.angle_list = list(reader)
        self.convert_plan_format(self.plan_type,self.angle_list)
        
        
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