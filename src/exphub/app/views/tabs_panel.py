"""Module for the Tab panel."""

from trame.widgets import html
from trame.widgets import vuetify3 as vuetify

from ..view_models.main import MainViewModel


class TabsPanel:
    """View class to render tabs."""

    def __init__(self, view_model: MainViewModel):
        # self.view_model = view_model
        # self.view_model.model_bind.connect("config")
        self.create_ui()

    def create_ui(self) -> None:
        with vuetify.VTabs(v_model=("active_tab", 0), classes="pl-5"):
            vuetify.VTab("IPTS Info", value=1)
            vuetify.VTab("Live Data Processing", value=2)
            vuetify.VTab("Experiment Steering", value=3)
            # vuetify.VTab("EIC Control",         value=4)
            # vuetify.VTab("Instrument Status", value=5)
            vuetify.VTab("Data Analysis", value=6)
            with vuetify.VTab(
                href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/BL12_ADnED_2D_4x4.bob&macros=%7B%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID305%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%7D",
                raw_attrs=['target="_blank"'],
            ):
                html.Span("Instrument Status")
                vuetify.VIcon("mdi-open-in-new", classes="ml-1")

            # vuetify.VTab("New Tab Template",    value=6)
