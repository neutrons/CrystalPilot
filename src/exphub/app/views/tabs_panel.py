"""Module for the Tab panel."""

from trame.widgets import client
from trame.widgets import vuetify3 as vuetify

from ..view_models.main import MainViewModel


class TabsPanel:
    """View class to render tabs."""

    def __init__(self, view_model: MainViewModel):
        self.view_model = view_model
        self.view_model.view_state_bind.connect("controls")
        self.create_ui()

    def create_ui(self) -> None:
        with client.DeepReactive("controls"):
            with vuetify.VTabs(v_model="controls.active_tab", classes="pl-5"):
                vuetify.VTab("IPTS Info", value=1)
                vuetify.VTab("Live Data Processing", value=2)
                vuetify.VTab("Experiment Steering", value=3)
                # vuetify.VTab("EIC Control", value=4)
                vuetify.VTab("Instrument Status", value=5)
                vuetify.VTab("Data Analysis", value=6)
                # vuetify.VTab("New Tab Template", value=7)
