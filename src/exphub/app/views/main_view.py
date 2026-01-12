"""Main file."""

import json
import logging
from html import unescape
from pathlib import Path
from re import findall
from typing import Any, Dict, Generator, List
from urllib.parse import unquote_plus

import dpath
from nova.mvvm.trame_binding import TrameBinding
from nova.trame import ThemedApp
from trame.app import get_server
from trame.widgets import client
from xmltodict import parse

from ..mvvm_factory import create_viewmodels
from ..view_models.main import MainViewModel
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
        self.create_ui()

    def create_ui(self) -> None:
        self.state.trame__title = "CrystalPilot"
        self.set_theme("CompactTheme")

        js_path = (Path(__file__).parent / "assets" / "webopi").resolve()
        self.server.enable_module(
            {
                "scripts": [
                    "assets/webopi/base64.js",
                    "assets/webopi/jquery-3.7.1.min.js",
                    "assets/webopi/pvws.js",
                    "assets/webopi/dbwr.js",
                ],
                "serve": {"assets/webopi": js_path},
            }
        )

        with super().create_ui() as layout:
            layout.toolbar_title.set_text("CrystalPilot")
            with layout.pre_content:
                TabsPanel(self.view_models["main"])
            with layout.content:
                TabContentPanel(
                    self.server,
                    self.view_models["main"],
                )

                with (
                    open("BL12_ADnED_2D_4x4.bob", mode="r") as xml_file,
                    open("BL12_ADnED_2D_4x4.macros", mode="r") as macros_file,
                ):
                    self.setup_webopi("model_cssstatus", xml_file.read(), macros_file.read())
            with layout.post_content:
                pass
            return layout

    def flatten(self, entry: Any) -> Generator[Any, None, None]:
        if isinstance(entry, List):
            for item in entry:
                yield from self.flatten(item)
        else:
            yield entry

    def replace_macros(self, pv_name: str, macro_dict: Dict[str, str]) -> str:
        full_name = pv_name
        for match in findall(r"\$\((\w+)\)", pv_name):
            try:
                full_name = full_name.replace(f"$({match})", macro_dict[match])
            except KeyError:
                return ""

        return full_name

    def setup_webopi(self, state_name: str, xml: str, macros: str) -> None:
        bob_dict = parse(xml)

        decoded_macros = unescape(unquote_plus(macros))
        macro_dict = json.loads(decoded_macros)

        pv_list = self.flatten(dpath.values(bob_dict, "**/pv_name"))
        full_pvs = {self.replace_macros(pv_name, macro_dict) for pv_name in pv_list}
        if "" in full_pvs:
            full_pvs.remove("")

        client.Script(
            """window.dbwr = new DisplayBuilderWebRuntime("wss://status.sns.ornl.gov/pvws/pv");"""
            """window.dbwr.pvws.open();"""
        )

        for pv in full_pvs:
            client.Script(f"""
                window.dbwr.pv_infos["{pv}"] = new PVInfo("{pv}");
                window.dbwr.pv_infos["{pv}"].subscriptions.push({{
                    "callback": (data) => {{
                        if (data.vtype === "VEnum") {{
                            data.value = Boolean(data.value);
                        }}
                        window.trame.state.state.{state_name}.pv_data["{pv}"] = data.value;
                        window.trame.state.flush();
                    }}
                }});

                setTimeout(() => {{
                    window.dbwr.pvws.subscribe("{pv}");
                }}, 1000);
            """)
