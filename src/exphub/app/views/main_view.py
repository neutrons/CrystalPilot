"""Main file."""

import logging
import os

from nova.epics.trame import get_epics_instance
from nova.mvvm.trame_binding import TrameBinding
from nova.trame import ThemedApp
from trame.app import get_server
from trame.widgets import client
from trame.widgets import vuetify3 as vuetify
from trame_client.widgets import html

# Importing the beamlines package registers every shipped beamline with the
# core registry. Must happen before active() is called.
from ... import beamlines  # noqa: F401
from ...core.beamline import BeamlineContext, active
from ..mvvm_factory import create_viewmodels
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
        self.beamline_ctx = BeamlineContext(active())
        self.view_models = create_viewmodels(binding)
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
                    size="large",
                    title="Toggle Agent Pane",
                )

            with layout.pre_content:
                TabsPanel(self.view_models["app_shell"])

            # Main content + inline chat panel side-by-side so the chat pane
            # squeezes the tab content instead of overlapping it.
            # The inner wrapper must be display:flex + flex-direction:column so
            # that VBoxLayout(stretch=True) children can grow vertically.
            with layout.content:
                with html.Div(style="display: flex; height: 100%; overflow: hidden;"):
                    with html.Div(
                        style="flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; overflow: hidden;"
                    ):
                        TabContentPanel(
                            self.server,
                            self.view_models["steering"],
                            self.view_models["app_shell"],
                        )
                    ChatPaneView(self.server, self.view_models["chat"])

            bob = self.beamline_ctx.bob_screen
            macros = self.beamline_ctx.bob_macros
            if bob is not None and macros is not None:
                with open(bob, mode="r") as xml_file, open(macros, mode="r") as macros_file:
                    self.epics.connect(xml_file.read(), macros_file.read(), 6)
            else:
                logger.warning(
                    "Active beamline %r has no .bob screen configured; "
                    "skipping EPICS connect()",
                    self.beamline_ctx.id,
                )

            self._subscribe_extra_pvs(self.beamline_ctx.extra_subscribe_pvs)

            return layout

    def _subscribe_extra_pvs(self, pv_names) -> None:
        """Subscribe to PVs not present in the main .bob file.

        Mirrors the per-PV ``client.Script`` template that
        ``nova.epics.trame.TrameEPICS.connect`` injects internally — the
        connect() entry point only walks PVs from a single XML, so any
        extra PVs (e.g. for a User Info panel not in the .bob screen) must
        be wired up separately via the same WebSocket runtime.
        """
        for pv in pv_names:
            client.Script(f"""
                window.dbwr.pv_infos["{pv}"] = new PVInfo("{pv}");
                window.dbwr.pv_infos["{pv}"].subscriptions.push({{
                    "callback": (data) => {{
                        if (data.vtype === "VEnum") {{
                            if (data.labels.length == 2) {{
                                data.value = Boolean(data.value);
                            }} else {{
                                data.value = data.text;
                            }}
                        }} else if (data.vtype === "VDouble" && data.precision !== undefined) {{
                            data.value = parseFloat(data.value).toFixed(data.precision);
                        }}
                        window.trame.state.state.epics.pv_data["{pv}"] = data.value;
                        window.trame.state.dirty("epics");
                        window.trame.state.flush();
                    }}
                }});

                setTimeout(() => {{
                    window.dbwr.pvws.subscribe("{pv}");
                }}, 1000);
            """)
