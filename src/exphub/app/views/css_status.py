"""Module for the CSS Status tab."""

from nova.trame.view.components import InputField
from nova.trame.view.layouts import GridLayout, HBoxLayout, VBoxLayout
from trame.widgets import plotly
from trame.widgets import vuetify3 as vuetify

from ..view_models.main import MainViewModel


class CSSStatusView:
    """View class for Plotly."""

    def __init__(self, view_model: MainViewModel) -> None:
        self.view_model = view_model
        self.view_model.cssstatus_bind.connect("model_cssstatus")
        self.create_ui()
        self.view_model.update_cssstatus_figure()

    def create_ui(self) -> None:
        with VBoxLayout(classes="border-md mb-1 pa-1", stretch=True):
            plotly.Figure()

            with HBoxLayout():
                InputField()
                InputField(type="checkbox")

            with HBoxLayout(gap="0.25em", valign="center"):
                vuetify.VBtn("Detail")
                vuetify.VBtn("Profiles")
                vuetify.VBtn("Clear Array & Counts")
                vuetify.VBtn("Reset ROI")
                InputField()
                InputField()
                InputField()
                InputField()
                InputField()
                InputField(type="checkbox")

        with GridLayout(columns=3, gap="0.25em", stretch=True):
            with VBoxLayout(classes="border-md pa-1", column_span=2):
                with vuetify.VTabs(classes="mb-1", style="height: 40px !important;"):
                    vuetify.VTab("TOF (All Modules)")
                    vuetify.VTab("d-Space (All Modules)")
                    vuetify.VTab("q-Space (All Modules)")
                    vuetify.VTab("d-Space (ROI Filtered)")
                    vuetify.VTab("q-Space (ROI Filtered)")

                with HBoxLayout():
                    vuetify.VBtn("Linear")
                    vuetify.VSpacer()
                    vuetify.VBtn("More Detail")

                plotly.Figure()

            with VBoxLayout(stretch=True):
                with VBoxLayout(classes="border-md pa-1", stretch=True):
                    plotly.Figure()
                    vuetify.VBtn("Cursor Detail")

                with GridLayout(classes="border-md pa-1", columns=2):
                    InputField()
                    InputField()
                    InputField()
                    InputField()
                    InputField()
                    InputField()
                    vuetify.VLabel("Running")
