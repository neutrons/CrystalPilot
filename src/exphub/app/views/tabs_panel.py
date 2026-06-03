"""Module for the Tab panel."""

from trame.widgets import client
from trame.widgets import vuetify3 as vuetify
from trame_client.widgets import html

from ..view_models.app_shell import AppShellViewModel


class TabsPanel:
    """Render the tab strip + a beamline selector inline at the same height.

    The selector binds to ``controls.beamline_id``; the AppShellViewModel's
    ``on_view_state_change`` callback detects the change and invokes
    ``switch_beamline`` to activate the new spec in the registry.
    """

    def __init__(self, view_model: AppShellViewModel):
        self.view_model = view_model
        self.view_model.view_state_bind.connect("controls")
        self.create_ui()

    def create_ui(self) -> None:
        with html.Div(
            style="display: flex; align-items: center; gap: 1rem; padding-right: 1rem; width: 100%;"
        ):
            with client.DeepReactive("controls"):
                with vuetify.VTabs(
                    v_model="controls.active_tab",
                    classes="pl-5",
                    style="flex: 1 1 auto; min-width: 0;",
                ):
                    vuetify.VTab("IPTS Info", value=1)
                    vuetify.VTab("Live Data Processing", value=2)
                    vuetify.VTab("Experiment Steering", value=3)
                    vuetify.VTab("Instrument Status", value=5)
                    vuetify.VTab("Data Analysis", value=6)
            vuetify.VSelect(
                v_model=("controls.beamline_id",),
                items=("controls.beamline_options", []),
                item_title="title",
                item_value="value",
                label="Beamline",
                density="compact",
                variant="outlined",
                hide_details=True,
                style="max-width: 220px; min-width: 160px; flex: 0 0 auto;",
            )
        with vuetify.VSnackbar(
            v_model="controls.beamline_switch_visible",
            timeout=6000,
            color="info",
            location="bottom",
        ):
            html.Span("{{ controls.beamline_switch_notice }}")
