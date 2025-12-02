"""View module for data analysis view."""

from nova.trame.view.components import InputField
from nova.trame.view.layouts import HBoxLayout, VBoxLayout
from trame.widgets import vuetify3 as vuetify

from ..view_models.main import MainViewModel


class DataAnalysisView:
    """View class for Plotly."""

    def __init__(self, view_model: MainViewModel) -> None:
        self.view_model = view_model
        self.view_model.dataanalysis_bind.connect("model_dataanalysis")
        self.create_ui()

    def create_ui(self) -> None:
        with VBoxLayout(classes="mb-2"):
            InputField(v_model="model_dataanalysis.data_dir", type="text", label="Data Directory")

        with HBoxLayout(classes="mb-2", gap="0.5em", valign="center"):
            InputField(
                v_model="model_dataanalysis.output_dir_nxv", type="text", label="Output Directory for NeuXtalViz"
            )
            vuetify.VBtn(
                "Data Visualization",
                color="primary",
                href="https://nova-test.ornl.gov/launch/nova-neutrons-trame-neuxtalviz-prototype",
                raw_attrs=['target="_blank"'],
            )

        with HBoxLayout(classes="mb-2", gap="0.5em", valign="center"):
            InputField(
                v_model="model_dataanalysis.output_dir_reduction", type="text", label="Output Directory for Reduction"
            )
            vuetify.VBtn(
                "Data Reduction",
                color="primary",
                href="https://nova.ornl.gov/launch/nova-neutrons-trame-topaz",
                raw_attrs=['target="_blank"'],
            )

        with HBoxLayout(classes="mb-2", gap="0.5em", valign="center"):
            InputField(
                v_model="model_dataanalysis.output_dir_reduction", type="text", label="Output Directory for Reduction"
            )
            vuetify.VBtn(
                "Structure Analysis",
                color="primary",
                href="https://nova.ornl.gov/launch/nova-interactive-tool-jana2020",
                raw_attrs=['target="_blank"'],
            )

        with HBoxLayout(classes="mb-2", gap="0.5em", valign="center"):
            # TODO: Need to figure out if this can run on NOVA.
            InputField(v_model="model_dataanalysis.output_dir_discus", type="text", label="Output Directory for Discus")
            vuetify.VBtn(
                "Diffuse Scattering Analysis",
                color="primary",
                href="http://10.159.209.93:8888/notebooks/demo/test.ipynb",
                raw_attrs=['target="_blank"'],
            )

        with HBoxLayout(classes="mb-2", gap="0.5em", valign="center"):
            InputField(v_model="model_dataanalysis.output_dir_olex2", type="text", label="Output Directory for Olex2")
            vuetify.VBtn(
                "Olex2",
                color="primary",
                href="https://nova.ornl.gov/launch/nova-interactive-tool-olex2",
                raw_attrs=['target="_blank"'],
            )

        with HBoxLayout(classes="mb-2", gap="0.5em", valign="center"):
            # TODO: Need to set this up similar to Olex2.
            InputField(v_model="model_dataanalysis.output_dir_shelx", type="text", label="Output Directory for ShelX")
            vuetify.VBtn("ShelX", click=self.open_shelx, color="primary")

    def open_shelx(self) -> None:
        """Open the Olex2 tab."""
        print("Open ShelX tab")
        # import os

        # os.system("~/run-olex2.sh")
        # os.system("shelxle")
        # os.system("/SNS/TOPAZ/shared/CrystalPilot/code/extbin/olex2")

    def open_diffuse_scattering_study(self) -> None:
        """Open the Data Refinement tab."""
        print("Open Discuss")
        # import os

        # os.system("~/run-discuss.sh")
