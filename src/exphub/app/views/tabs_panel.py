"""Module for the Tab panel."""

from trame.widgets import client
from trame.widgets import html
from trame.widgets import vuetify3 as vuetify

from ..view_models.main import MainViewModel


class TabsPanel:
    """View class to render the tab strip + the beamline selector.

    The beamline selector sits at the right end of the tab strip (same row,
    same vertical height as the tab labels) so it is always visible regardless
    of which tab is active.
    """

    def __init__(self, view_model: MainViewModel):
        self.view_model = view_model
        self.view_model.view_state_bind.connect("controls")
        self.create_ui()

    def create_ui(self) -> None:
        with client.DeepReactive("controls"):
            # display:flex row: tabs grow to fill, selector hugs the right edge.
            with html.Div(
                style=(
                    "display: flex;"
                    "align-items: center;"
                    "gap: 1rem;"
                    "padding-right: 1rem;"
                    "width: 100%;"
                )
            ):
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
                # Right-aligned compact beamline selector.
                vuetify.VSelect(
                    v_model=("controls.beamline_id",),
                    items=("controls.beamline_options",),
                    item_title="title",
                    item_value="value",
                    label="Beamline",
                    density="compact",
                    variant="outlined",
                    hide_details=True,
                    style="max-width: 220px; min-width: 160px; flex: 0 0 auto;",
                    update_modelValue=(
                        self.view_model.switch_beamline,
                        "[$event]",
                    ),
                )
            # Snackbar surfacing the post-switch notice (restart hint).
            vuetify.VSnackbar(
                v_model=("controls.beamline_switch_notice != ''",),
                text=("controls.beamline_switch_notice",),
                timeout=6000,
                update_modelValue=(
                    "controls.beamline_switch_notice = ''",
                    "[$event]",
                ),
            )
