"""Module for the Sample Tab 2."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nova.trame.view.components import InputField, RemoteFileInput
from nova.trame.view.layouts import GridLayout
from trame.widgets import vuetify3 as vuetify

if TYPE_CHECKING:
    from ...techniques.single_crystal.view_models.steering import SingleCrystalSteeringViewModel


# In your View setup
class EICControlView:
    """Sample tab 2 view class. Renders text input for user password."""

    def __init__(self, view_model: SingleCrystalSteeringViewModel) -> None:
        self.view_model = view_model
        self.view_model.eiccontrol_bind.connect("model_eiccontrol")
        self.view_model.experimentinfo_bind.connect("model_experimentinfo")
        self.create_ui()

    def create_ui(self) -> None:
        RemoteFileInput(v_model="model_eiccontrol.token_file", base_paths=["/HFIR", "/SNS"])
        with GridLayout(columns=1):
            vuetify.VBtn("Authenticate", click=self.view_model.call_load_token)
        InputField(v_model="model_eiccontrol.is_simulation", type="checkbox")
        InputField(v_model="model_experimentinfo.ipts_number")
        with GridLayout(columns=1):
            vuetify.VBtn("Submit through EIC", click=self.view_model.submit_angle_plan)

        with GridLayout(columns=1):
            vuetify.VBanner(
                v_if="model_eiccontrol.eic_submission_success",
                text="Submission Successful.",
                # text=(
                #   "Submission Successful. "
                #   "Scan ID: {{model_eiccontrol.eic_submission_scan_id}}, "
                #   "Message: {{model_eiccontrol.eic_submission_message}}",
                # ),
                color="success",
            )
