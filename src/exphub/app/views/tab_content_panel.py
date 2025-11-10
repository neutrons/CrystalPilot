"""Module for the Tab Content panel."""

from trame.widgets import vuetify3 as vuetify
from trame_server import Server

from ..view_models.main import MainViewModel
from .angle_plan import AnglePlanView
from .css_status import CSSStatusView
from .data_analysis import DataAnalysisView
from .experiment_info import ExperimentInfoView
from .temporal_analysis import TemporalAnalysisView  # Import the new view


class TabContentPanel:
    """View class to render content for a selected tab."""

    def __init__(self, server: Server, view_model: MainViewModel) -> None:
        self.view_model = view_model
        self.server = server
        self.ctrl = server.controller
        self.create_ui()
        self.view_model.is_under_development_bind.connect("is_under_development")
        self.view_model.is_uninterruptable_bind.connect("is_uninterruptable")

    def create_ui(self) -> None:
        with vuetify.VWindow(v_model="active_tab"):
            with vuetify.VWindowItem(value=1):
                ExperimentInfoView(self.view_model)
            with vuetify.VWindowItem(value=2):
                TemporalAnalysisView(self.view_model)
            with vuetify.VWindowItem(value=3):
                AnglePlanView(self.view_model)
            # with vuetify.VWindowItem(value=4):
            #     EICControlView(self.view_model)
            with vuetify.VWindowItem(value=5):
                CSSStatusView(self.view_model)
            with vuetify.VWindowItem(value=6):
                DataAnalysisView(self.view_model)
            # with vuetify.VWindowItem(value=6):
            #     NewTabTemplateView(self.view_model)

        with vuetify.VDialog(v_model="is_under_development", max_width="500px"):
            with vuetify.VCard():
                with vuetify.VCardTitle("Under Development"):
                    print("Under Development")
                    vuetify.VCardText(
                        "This feature is currently under development.", classes="text-caption text-center"
                    )
                with vuetify.VCardActions():
                    vuetify.VBtn(
                        "OK", click=self.view_model.close_under_development_dialog, color="primary", block=True
                    )
                    # vuetify.VBtn("OK",  color="primary", block=True)

        with vuetify.VDialog(v_model="is_uninterruptable", max_width="500px"):
            with vuetify.VCard():
                with vuetify.VCardTitle("Waiting for Algorithm"):
                    vuetify.VCardText(
                        "Algorithm is running in background, waiting for completion.",
                        classes="text-caption text-center",
                    )

    #                    with vuetify.VCardActions():
    #                        vuetify.VBtn("OK", click=self.view_model.close_under_development_dialog, color="primary",
    #                           block=True)
    # vuetify.VBtn("OK",  color="primary", block=True)

    def open_data_visualization(self) -> None:
        """Open the Data Visualization tab."""
        # self.view_model.call_nxv()
        import os

        os.system("~/run-nxv.sh")
        print("Open Data Visualization tab")

    def open_data_reduction(self) -> None:
        """Open the Data Reduction tab."""
        print("Open Data Reduction tab")

    def open_data_refinement(self) -> None:
        """Open the Data Refinement tab."""
        print("Open Data Refinement tab")
