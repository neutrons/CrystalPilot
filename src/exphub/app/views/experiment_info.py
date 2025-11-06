"""Module for the System tab."""

from nova.trame.view.components import InputField, RemoteFileInput
from nova.trame.view.layouts import GridLayout


class ExperimentInfoView:
    """View class to render the System tab."""

    def __init__(self, view_model):
        self.view_model = view_model

        self.view_model.experimentinfo_bind.connect("config")
        self.create_ui()

    def create_ui(self) -> None:
        with GridLayout():
            InputField(v_model="config.expName")
            InputField(v_model="config.ipts_number")

        with GridLayout():
            InputField(
                v_model="config.instrument",
                items="config.options.instrument_list",
                type="select",
            )
            InputField(v_model="config.molecularFormula")
            InputField(
                v_model="config.crystalsystem",
                items="config.options.crystalsystem_list",
                type="select",
            )
            InputField(
                v_model="config.pointGroup",
                items="config.options.pointGroup_list",
                type="select",
            )
            InputField(
                v_model="config.centering",
                items="config.options.centering_list",
                type="select",
            )
            RemoteFileInput(
                v_model="config.UBFileName",
            )
            RemoteFileInput(
                v_model="config.calFileName",
            )
        with GridLayout(columns=2):
            InputField(
                v_model="config.minDSpacing",
            )
            InputField(
                v_model="config.maxDSpacing",
            )

    def save_settings(self):
        # Placeholder function to handle saving settings
        print("Settings saved")
