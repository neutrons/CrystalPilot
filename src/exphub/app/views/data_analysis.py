
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
            InputField(v_model="model_dataanalysis.output_dir", type="text", label="Output Directory")
        
           # with vuetify.VCardActions():
           #     vuetify.VBtn("Data Visualization", click=self.open_data_visualization)
           #     vuetify.VBtn("Data Reduction", click=self.open_data_reduction)
           #     vuetify.VBtn("Structure Analysis", click=self.open_data_refinement)
           #     vuetify.VBtn("Diffuse Scattering Study", click=self.open_diffuse_scattering_study)
            with vuetify.VCardActions():
                vuetify.VBtn("Data Visualization", click=self.open_data_visualization)

            with vuetify.VCardActions():
             with vuetify.VTab(href="https://nova.ornl.gov/single-crystal-diffraction", raw_attrs=['''target="_blank"'''],classes="justify-start"):
                html.Span("Data Reduction & Structure Analysis", classes="mr-1")
                vuetify.VIcon("mdi-open-in-new")
            #with vuetify.VCardActions():
            #    vuetify.VBtn("Diffuse Scattering Study", click=self.open_diffuse_scattering_study)
            with vuetify.VCardActions():
             with vuetify.VTab(href="https://colab.research.google.com/github/tproffen/DiffuseCode/blob/python-interface/python/Notebooks/APITests.ipynb",classes="justify-start", raw_attrs=['''target="_blank"''']):
                html.Span("Diffuse Scattering Study", classes="mr-1")
                vuetify.VIcon("mdi-open-in-new")
        
    def open_data_visualization(self) -> None:
        """Open the Data Visualization tab."""
        #self.view_model.call_nxv()
        import os
        os.system("~/run-nxv-0.sh")
        print("Open Data Visualization tab")
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
        