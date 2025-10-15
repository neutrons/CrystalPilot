
import plotly.graph_objects as go
from nova.trame.view.components import InputField
from nova.trame.view.layouts import GridLayout, HBoxLayout
from trame.widgets import plotly

from typing import List, Dict
from nova.trame.view.components import InputField,RemoteFileInput
from ..view_models.main import MainViewModel
from nova.trame.view.layouts import GridLayout, HBoxLayout
from trame.widgets import vuetify3 as vuetify


from ..view_models.main import MainViewModel

from trame.widgets import html

class DataAnalysisView:
    """View class for Plotly."""

    def __init__(self, view_model: MainViewModel) -> None:
        self.view_model = view_model
        self.view_model.dataanalysis_bind.connect("model_dataanalysis")
        self.create_ui()


    def create_ui(self) -> None:
        with GridLayout(columns=1, classes="mb-2"):
            InputField(v_model="model_dataanalysis.data_dir", type="text", label="Data Directory")
            #InputField(v_model="model_dataanalysis.output_dir", type="text", label="Output Directory")
        
           # with vuetify.VCardActions():
           #     vuetify.VBtn("Data Visualization", click=self.open_data_visualization)
           #     vuetify.VBtn("Data Reduction", click=self.open_data_reduction)
           #     vuetify.VBtn("Structure Analysis", click=self.open_data_refinement)
           #     vuetify.VBtn("Diffuse Scattering Study", click=self.open_diffuse_scattering_study)
        with GridLayout(columns=2, classes="mb-2"):
            InputField(v_model="model_dataanalysis.output_dir_nxv", type="text", label="Output Directory for NeuXstalViz")
            #with vuetify.VCardActions():
            #    vuetify.VBtn("Data Visualization", click=self.open_data_visualization)
            vuetify.VBtn("Data Visualization", click=self.open_data_visualization, color="primary", style="align-self: center;")

        with GridLayout(columns=2, classes="mb-2"):
            InputField(v_model="model_dataanalysis.output_dir_reduction", type="text", label="Output Directory for Reduction")
        #vuetify.VBtn(
        #    "Data Reduction & Structure Analysis",
        #    href="https://nova.ornl.gov/single-crystal-diffraction",
        #    target="_blank",
        #    color="primary",
        #    style="align-self: center;",
        #    raw_attrs=['rel="noopener noreferrer"']
        #)
        #vuetify.VIcon("mdi-open-in-new")
            vuetify.VBtn(
                "Data Reduction & Structure Analysis",
                click="window.open('https://nova.ornl.gov/single-crystal-diffraction', '_blank')",
                target="_blank",
                color="primary",
                style="align-self: center;",
                raw_attrs=['rel="noopener noreferrer"']
            )
        #    vuetify.VIcon("mdi-open-in-new")

        with GridLayout(columns=2, classes="mb-2"):
            InputField(v_model="model_dataanalysis.output_dir_discus", type="text", label="Output Directory for Discus")
            vuetify.VBtn(
                    "Diffuse Scattering Analysis",
                    click="window.open('http://10.159.209.93:8888/notebooks/demo/test.ipynb', '_blank')",
                    target="_blank",
                    color="primary",
                    style="align-self: center;"
                )
        with GridLayout(columns=2, classes="mb-2"):
            InputField(v_model="model_dataanalysis.output_dir_olex2", type="text", label="Output Directory for Olex2")
            vuetify.VBtn("Olex2", click=self.open_olex2, color="primary",style="align-self: center;")

        with GridLayout(columns=2, classes="mb-2"):
            InputField(v_model="model_dataanalysis.output_dir_shelx", type="text", label="Output Directory for ShelX")
            vuetify.VBtn("ShelX", click=self.open_shelx, color="primary",style="align-self: center;")

#            with vuetify.VCardActions():
#                vuetify.VBtn("Data Visualization", click=self.open_data_visualization)
#
#            with vuetify.VCardActions():
#             with vuetify.VTab(href="https://nova.ornl.gov/single-crystal-diffraction", raw_attrs=['''target="_blank"'''],classes="justify-start"):
#                html.Span("Data Reduction & Structure Analysis", classes="mr-1")
#                vuetify.VIcon("mdi-open-in-new")
#            #with vuetify.VCardActions():
#            #    vuetify.VBtn("Diffuse Scattering Study", click=self.open_diffuse_scattering_study)
#            with vuetify.VCardActions():
#            # with vuetify.VTab(href="https://colab.research.google.com/github/tproffen/DiffuseCode/blob/python-interface/python/Notebooks/APITests.ipynb",classes="justify-start", raw_attrs=['''target="_blank"''']):
#             with vuetify.VTab(href="http://localhost:8888/notebooks/demo/test.ipynb",classes="justify-start", raw_attrs=['''target="_blank"''']):
#                html.Span("Diffuse Scattering Study", classes="mr-1")
#                vuetify.VIcon("mdi-open-in-new")
#
#            with vuetify.VCardActions():
#                vuetify.VBtn("Olex2", click=self.open_olex2, color="primary")
#
#
#            #html.Iframe(src="https://colab.research.google.com/github/tproffen/DiffuseCode/blob/python-interface/python/Notebooks/APITests.ipynb", style="width:100%;height:500px;")
#            #html.Iframe(src="http://localhost:8888/notebooks/test.ipynb", style="width:100%;height:500px;", )
#
#            with vuetify.VDialog(v_model="show_notebook_dialog", max_width=900):
#                    with vuetify.VCard():
#                        vuetify.VCardTitle("Load Python Notebook")
#                        with vuetify.VCardText():
#
#                            #InputField(v_model="notebook_url", label="Notebook URL", type="text")
#                            #html.Iframe(src="{{ notebook_url }}", style="width:100%;height:500px;", v_if="notebook_url")
#                            #InputField(v_model="https://colab.research.google.com/github/tproffen/DiffuseCode/blob/python-interface/python/Notebooks/APITests.ipynb", label="Notebook URL", type="text")
#                            #html.Iframe(src="https://colab.research.google.com/github/tproffen/DiffuseCode/blob/python-interface/python/Notebooks/APITests.ipynb", style="width:100%;height:500px;", v_if="notebook_url")
#                            html.Iframe(src="http://localhost:8888/notebooks/Untitled.ipynb", style="width:100%;height:500px;", v_if="notebook_url")
#                        with vuetify.VCardActions():
#                            vuetify.VSpacer()
#                            vuetify.VBtn("Close", click="show_notebook_dialog = false", color="primary")
#
#            #vuetify.VBtn("Open Notebook", click="show_notebook_dialog = true", color="secondary")

    def open_data_visualization(self) -> None:
        """Open the Data Visualization tab."""
        #self.view_model.call_nxv()
        import os
        os.system("~/run-nxv-0.sh")
        #os.system("/SNS/TOPAZ/shared/CrystalPilot/code/extbin/nxv.sh")
        print("Open Data Visualization tab")
    def open_olex2(self) -> None:
        """Open the Olex2 tab."""
        print("Open Olex2 tab")
        import os
        #os.system("~/run-olex2.sh")
        os.system("olex2")
        #os.system("/SNS/TOPAZ/shared/CrystalPilot/code/extbin/olex2")

    def open_shelx(self) -> None:
        """Open the Olex2 tab."""
        print("Open ShelX tab")
        import os
        #os.system("~/run-olex2.sh")
        os.system("shelxle")
        #os.system("/SNS/TOPAZ/shared/CrystalPilot/code/extbin/olex2")


    def open_data_reduction(self) -> None:
        """Open the Data Reduction tab."""
        print("Open Data Reduction tab")
    def open_data_refinement(self) -> None:
        """Open the Data Refinement tab."""
        print("Open Data Refinement tab")
        
    def open_diffuse_scattering_study(self) -> None:
        """Open the Data Refinement tab."""
        print("Open Discuss")
        import os
        os.system("~/run-discuss.sh")
    
        
