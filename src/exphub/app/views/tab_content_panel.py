"""Module for the Tab Content panel."""

import logging

from nova.trame.view.layouts import VBoxLayout
from trame.widgets import vuetify3 as vuetify
from trame_server import Server

from ...core.beamline import active as _active_beamline
from ..view_models.main import MainViewModel
from .angle_plan import AnglePlanView
from .data_analysis import DataAnalysisView
from .experiment_info import ExperimentInfoView
from .temporal_analysis import TemporalAnalysisView  # Import the new view

logger = logging.getLogger(__name__)


class TabContentPanel:
    """View class to render content for a selected tab."""

    def __init__(self, server: Server, view_model: MainViewModel) -> None:
        self.view_model = view_model
        self.server = server
        self.ctrl = server.controller
        self.create_ui()

    def create_ui(self) -> None:
        with VBoxLayout(v_show="controls.active_tab == 1", stretch=True):
            ExperimentInfoView(self.view_model)
        with VBoxLayout(v_show="controls.active_tab == 2", stretch=True):
            TemporalAnalysisView(self.view_model)
        with VBoxLayout(v_show="controls.active_tab == 3", stretch=True):
            AnglePlanView(self.view_model)
        # with VBoxLayout(v_show="controls.active_tab == 4", stretch=True):
        #     EICControlView(self.view_model)
        with VBoxLayout(v_if="controls.active_tab == 5", stretch=True):
            css_status_factory = _active_beamline().tabs.css_status
            if css_status_factory is not None:
                css_status_factory(self.view_model)
            else:
                logger.warning(
                    "Active beamline %r does not provide a css_status tab; "
                    "Instrument Status tab will be blank.",
                    _active_beamline().id,
                )
                vuetify.VAlert(
                    text="Instrument Status is not configured for this beamline.",
                    type="info",
                    variant="tonal",
                )
        with VBoxLayout(v_show="controls.active_tab == 6", stretch=True):
            DataAnalysisView(self.view_model)
        # with VBoxLayout(v_show="controls.active_tab == 7", stretch=True):
        #     NewTabTemplateView(self.view_model)

        with vuetify.VDialog(v_model="controls.is_under_development", max_width="500px"):
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

        with vuetify.VDialog(v_model="controls.is_uninterruptable", max_width="500px"):
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
