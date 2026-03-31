"""Main file."""

import logging
import os

from nova.epics.trame import get_epics_instance
from nova.mvvm.trame_binding import TrameBinding
from nova.trame import ThemedApp
from trame.app import get_server
from trame.widgets import vuetify3 as vuetify
from trame_client.widgets import html

from ..mvvm_factory import create_viewmodels
from ..view_models.main import MainViewModel
from .chat_pane import ChatPaneView
from .tab_content_panel import TabContentPanel
from .tabs_panel import TabsPanel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MainApp(ThemedApp):
    """Main application view class. Calls rendering of nested UI elements."""

    def __init__(self) -> None:
        super().__init__()
        self.server = get_server(None, client_type="vue3")
        binding = TrameBinding(self.server.state)
        self.server.state.trame__title = "CrystalPilot"
        self.view_models = create_viewmodels(binding)
        self.view_model: MainViewModel = self.view_models["main"]
        self.epics = get_epics_instance()
        self.create_ui()

    def create_ui(self) -> None:
        self.set_theme("CompactTheme")
        self.state.trame__title = "CrystalPilot"

        # Suppress the NOVA Examples / Tutorial / Documentation buttons that
        # ThemedApp injects when PIXI_ENVIRONMENT_NAME != "production".
        os.environ["PIXI_ENVIRONMENT_NAME"] = "production"

        with super().create_ui() as layout:
            layout.toolbar_title.set_text("CrystalPilot")

            # Agent toggle button in toolbar (top-right, next to exit button)
            with layout.actions:
                vuetify.VBtn(
                    icon="mdi-robot-outline",
                    click=self.view_models["chat"].toggle_drawer,
                    variant="text",
                    size="small",
                    title="Toggle Agent Pane",
                )

            with layout.pre_content:
                TabsPanel(self.view_models["main"])

            # Main content + inline chat panel side-by-side so the chat pane
            # squeezes the tab content instead of overlapping it.
            with layout.content:
                with html.Div(style="display: flex; height: 100%; overflow: hidden;"):
                    with html.Div(style="flex: 1 1 0; overflow: hidden;"):
                        TabContentPanel(
                            self.server,
                            self.view_models["main"],
                        )
                    ChatPaneView(self.server, self.view_models["chat"])

            with (
                open("BL12_ADnED_2D_4x4.bob", mode="r") as xml_file,
                open("BL12_ADnED_2D_4x4.macros", mode="r") as macros_file,
            ):
                self.epics.connect(xml_file.read(), macros_file.read(), 6)

            return layout
