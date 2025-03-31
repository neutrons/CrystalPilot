from pydantic import BaseModel, Field, computed_field, field_validator, model_validator
from typing import List, Dict
import csv
import plotly.graph_objects as go

import numpy as np


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
    polyhedrons: List = Field(default=[], title="Polyhedrons", description="List of polyhedrons to be displayed")

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
    is_showing_coverage: bool = Field(default=False, title="Is Showing Coverage", description="Flag to indicate if the coverage is being shown")
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
    wait_for_list: List[str] = Field(default=["PCharge", "seconds"])

    target_coverage: float = Field(default=0.9, title="Target coverage", description="Target coverage for the experiment")
    qpane_cones: List = Field(default=[], title="Q Pane Cones", description="List of Q pane cones to be displayed")



    instrument        : str = Field(default="TOPAZ", title="Instrument Name", description="Name of the instrument" )
    wavelength        : float = Field(default=1.0, title="Wavelength", description="Wavelength of the beam", type="float")
    axes              : List = Field(default=[[0,1,0]], title="Axes", description="List of axes to be used for the angle plan")
    limits            : List = Field(default=[0, 360], title="Limits", description="Limits of the axes") 
    UB                : List = Field(default=[[-0.06196579 ,-0.0646735 ,  0.00629365],
                                        [ 0.05857223, -0.05941086, -0.03262031],
                                        [ 0.02816059, -0.01873959,  0.08169699]], title="UB Matrix", description="UB matrix of the crystal")
    d_min             : float = Field(default=0.5, title="d_min", description="d_min of the crystal")
    d_max             : float = Field(default=10, title="d_max", description="d_max of the crystal")
    offset            : float = Field(default=0, title="Offset", description="Offset of the crystal")
    point_group       : str = Field(default="m-3", title="Point Group", description="Point group of the crystal")
    lattice_centering : str = Field(default="P", title="Lattice Centering", description="Lattice centering of the crystal")

 
    
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




    # note to symmetry:
    # 1. mantid has 
    #   # Create point group
    #   point_group = PointGroupFactory.createPointGroup(point_group_symbol)
    #   # Get symmetry operations
    #   sym_ops = point_group.getSymmetryOperations()
    # 2. symmetryopreation should have matrix() method
    #     not work in python
    # 3. sym_op.transformHKL([1,0,0])           # qspace
    #    sym_op.transformCoordinate[1,0,0])     # real space
    #    have strange  behaviro:  eg
    #    
    #         
    #         pg = PointGroupFactory.createPointGroup('6/mmm')
    #         s=pg.getSymmetryOperationStrings
    #         s
    #         Out[79]: <bound method getSymmetryOperationStrings of PointGroupFactory.createPointGroup("6/mmm")>
    #         pg.getSymmetryOperationStrings()
    #         Out[80]: <mantid.kernel._kernel.std_vector_str at 0x7ad2afb57df0>
    #         s=pg.getSymmetryOperationStrings()
    #         s
    #         Out[83]: <mantid.kernel._kernel.std_vector_str at 0x7ad2afb84970>
    #         s[0]
    #         Out[84]: '-x+y,-x,-z'
    #     not rotation matrix

    ####################
    # change strategey to use repeated q grids
    ####################
    #
    #def angleplan(self, instrument, logs, wavelength,peaks,laue):



#
#    def get_rotation_matrix(self, chi: float, phi: float, omega: float) -> np.array:
#            rotation_matrix_omega = np.array([
#                [np.cos(np.radians(omega)), 0, np.sin(np.radians(omega))],
#                [0, 1, 0],
#                [-np.sin(np.radians(omega)), 0, np.cos(np.radians(omega))]
#            ])
#            rotation_matrix_chi = np.array([
#                [np.cos(np.radians(chi)), -np.sin(np.radians(chi)), 0],
#                [np.sin(np.radians(chi)), np.cos(np.radians(chi)), 0],
#                [0, 0, 1]
#            ])
#            rotation_matrix_phi = np.array([
#                [np.cos(np.radians(phi)), 0, np.sin(np.radians(phi))],
#                [0, 1, 0],
#                [-np.sin(np.radians(phi)), 0, np.cos(np.radians(phi))]
#            ])
#            # Combine the rotation matrices
#            rotation_matrix = rotation_matrix_omega @ rotation_matrix_chi @ rotation_matrix_phi
#            return rotation_matrix
 
    def get_rotation_matrix(self, chi: float, phi: float, omega: float) :
            rotation_matrix_omega = [
                [np.cos(np.radians(omega)), 0, np.sin(np.radians(omega))],
                [0, 1, 0],
                [-np.sin(np.radians(omega)), 0, np.cos(np.radians(omega))]
            ]
            rotation_matrix_chi = [
                [np.cos(np.radians(chi)), -np.sin(np.radians(chi)), 0],
                [np.sin(np.radians(chi)), np.cos(np.radians(chi)), 0],
                [0, 0, 1]
            ]
            rotation_matrix_phi = [
                [np.cos(np.radians(phi)), 0, np.sin(np.radians(phi))],
                [0, 1, 0],
                [-np.sin(np.radians(phi)), 0, np.cos(np.radians(phi))]
            ]
            # Combine the rotation matrices
            rotation_matrix = (np.array(rotation_matrix_omega) @ np.array(rotation_matrix_chi) @ np.array(rotation_matrix_phi)).tolist()
            return rotation_matrix
 




    def update_polyhedron_angle_list(self) -> List:
        polyhedron_original_list=self.qpane_cones.copy()

        polyhedron_angle_list=[]
        for p0 in polyhedron_original_list:
            v0,f0=p0['qvertices'],p0['qfaces']
            for angle in self.angle_list:
                # Extract vertices and faces
                chi,phi,omega = angle["chi"],angle["phi"],angle["omega"]
                R=self.get_rotation_matrix(chi, phi, omega)
                v = (R @ v0).tolist()  # Convert numpy array to list

                polyhedron_angle_list.append((v, f0))
        return polyhedron_angle_list


    def get_figure_coverage(self) -> go.Figure:
        # Implement the submit logic here
       

        def get_polyhedron_plot(vertices,faces) ->go.Mesh3d:
            #px1 = vertices[:, 0].tolist()
            #px2 = vertices[:, 0].tolist()
            #px=np.array(px1+px2)
            #py1 = vertices[:, 1].tolist()
            #py2 = vertices[:, 1].tolist()
            #py=np.array(py1+py2)
            #pz1 = vertices[:, 2].tolist()
            #pz2 = vertices[:, 2].tolist()
            #pz=np.array(pz1+pz2)

            #pi1=list(faces[:, 1])
            #pi2=list(faces[:, 3])
            #pi=np.array(pi1+pi2)
            #pj1=list(faces[:, 2])
            #pj2=list(faces[:, 4])
            #pj=np.array(pj1+pj2)
            #pk1=list(faces[:, 3])
            #pk2=list(faces[:, 1])
            #pk=np.array(pk1+pk2)
            px1 = vertices[:, 0].tolist()
            px2 = vertices[:, 0].tolist()
            px=px1+px2
            py1 = vertices[:, 1].tolist()
            py2 = vertices[:, 1].tolist()
            py=py1+py2
            pz1 = vertices[:, 2].tolist()
            pz2 = vertices[:, 2].tolist()
            pz=pz1+pz2

            pi1=list(faces[:, 1])
            pi2=list(faces[:, 3])
            pi=pi1+pi2
            pj1=list(faces[:, 2])
            pj2=list(faces[:, 4])
            pj=pj1+pj2
            pk1=list(faces[:, 3])
            pk2=list(faces[:, 1])
            pk=pk1+pk2
            polyhedron_plot = go.Mesh3d( x=px, y=py, z=pz, i=pi, j=pj, k=pk,
                    color='lightblue', opacity=0.50, alphahull=0)
            return polyhedron_plot

        #vertices = np.array([
        #    [0, 0, 0],
        #    [1, 0, 0],
        #    [1, 1, 0],
        #    [0, 1, 0],
        #    [0, 0, 1],
        #    [1, 0, 1],
        #    [1, 1, 1],
        #    [0, 1, 1],
        #])
        
        ## Define faces
        #faces = np.array([
        #    [4, 0, 1, 2, 3],  # bottom
        #    [4, 4, 5, 6, 7],  # top
        #    [4, 0, 1, 5, 4],  # front
        #    [4, 1, 2, 6, 5],  # right
        #    [4, 2, 3, 7, 6],  # back
        #    [4, 3, 0, 4, 7],  # left
        #])

        #polyhedrons=[
        #    (vertices, faces),
        #    (vertices+0.5, faces)
        #]



        fig=go.Figure()
        for polyhedron in self.polyhedrons:
            # Extract vertices and faces
            vertices, faces = polyhedron
            # Create a mesh plot
            polyhedron_plot = get_polyhedron_plot(vertices,faces)
            fig.add_trace(polyhedron_plot)

        fig.update_layout(
            scene=dict(
            xaxis_title='X Axis',
            yaxis_title='Y Axis',
            zaxis_title='Z Axis',
            aspectmode='data'
            ),
            title='3D Polyhedron Visualization'
        )
        return fig


        #self.is_under_development = True

