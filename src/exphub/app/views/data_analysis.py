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
        with VBoxLayout():
            InputField(v_model="model_dataanalysis.data_dir", type="text", label="Data Directory")

        with HBoxLayout(gap="0.5em", valign="center"):
            InputField(
                v_model="model_dataanalysis.output_dir_nxv", type="text", label="Output Directory for NeuXtalViz"
            )
            vuetify.VBtn(
                "Data Visualization",
                color="primary",
                href="https://nova-test.ornl.gov/launch/nova-neutrons-trame-neuxtalviz-prototype",
                raw_attrs=['target="_blank"'],
            )

        with HBoxLayout(gap="0.5em", valign="center"):
            InputField(
                v_model="model_dataanalysis.output_dir_reduction", type="text", label="Output Directory for Reduction"
            )
            vuetify.VBtn(
                "Data Reduction",
                color="primary",
                href="https://nova.ornl.gov/launch/nova-neutrons-trame-topaz",
                raw_attrs=['target="_blank"'],
            )

        with HBoxLayout(gap="0.5em", valign="center"):
            InputField(
                v_model="model_dataanalysis.output_dir_reduction", type="text", label="Output Directory for Reduction"
            )
            vuetify.VBtn(
                "Structure Analysis",
                color="primary",
                href="https://nova.ornl.gov/launch/nova-interactive-tool-jana2020",
                raw_attrs=['target="_blank"'],
            )

        with HBoxLayout(gap="0.5em", valign="center"):
            InputField(v_model="model_dataanalysis.output_dir_discus", type="text", label="Output Directory for Discus")
            vuetify.VBtn(
                "Diffuse Scattering Analysis",
                color="primary",
                href="https://nova.ornl.gov/launch/nova-interactive-tool-discus",
                raw_attrs=['target="_blank"'],
            )

        with HBoxLayout(gap="0.5em", valign="center"):
            InputField(v_model="model_dataanalysis.output_dir_olex2", type="text", label="Output Directory for Olex2")
            vuetify.VBtn(
                "Olex2",
                color="primary",
                href="https://nova.ornl.gov/launch/nova-interactive-tool-olex2",
                raw_attrs=['target="_blank"'],
            )

        with HBoxLayout(gap="0.5em", valign="center"):
            InputField(v_model="model_dataanalysis.output_dir_shelx", type="text", label="Output Directory for ShelX")
            vuetify.VBtn(
                "ShelXle",
                color="primary",
                href="https://nova.ornl.gov/launch/nova-interactive-tool-shelxle",
                raw_attrs=['target="_blank"'],
            )
