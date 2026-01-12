"""Module for the CSS Status tab."""

from typing import Any

from nova.trame.view.components import InputField
from nova.trame.view.layouts import GridLayout, HBoxLayout, VBoxLayout
from trame.widgets import plotly
from trame.widgets import vuetify3 as vuetify
from trame_client.widgets.core import AbstractElement

from ..view_models.main import MainViewModel


class PVInput(InputField):
    """Creates a read-only (by default) InputField that connects to the PV data object."""

    def __new__(cls, pv_name: str, append: str = "", **kwargs: Any) -> AbstractElement:
        readonly = kwargs.pop("readonly", True)
        if append:
            with super().__new__(
                cls,
                v_if=f"'{pv_name}' in model_cssstatus.pv_data",
                v_model=f"model_cssstatus.pv_data['{pv_name}']",
                readonly=readonly,
                **kwargs,
            ) as element:
                with vuetify.Template(v_slot_append_inner=True):
                    vuetify.VLabel(append)

            return element

        return super().__new__(
            cls,
            v_if=f"'{pv_name}' in model_cssstatus.pv_data",
            v_model=f"model_cssstatus.pv_data['{pv_name}']",
            readonly=readonly,
            **kwargs,
        )


class CSSStatusView:
    """View class for Plotly."""

    def __init__(self, view_model: MainViewModel) -> None:
        self.view_model = view_model
        self.view_model.cssstatus_bind.connect("model_cssstatus")
        self.create_ui()
        self.view_model.update_cssstatus_figure()

    def create_ui(self) -> None:
        with VBoxLayout(classes="border-md mb-1 px-2 py-1", stretch=True):
            plotly.Figure()

            with HBoxLayout():
                PVInput("BL12:Det:N1:Det4:XY:Scale:ManualMin", label="Min")
                PVInput("BL12:Det:N1:Det4:XY:ROI:0:Use", label="Autoscale", type="checkbox")

            with HBoxLayout(gap="0.25em", valign="center"):
                vuetify.VBtn(
                    "Detail",
                    href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/../../share/opi/ADnEDv3/ADnED_XYArray.opi&macros=%7B%26quot%3BDET%26quot%3B%3A%26quot%3B4%26quot%3B%2C%26quot%3BDETNAME%26quot%3B%3A%26quot%3BMain%20Detector%20(4x4)%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID140%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%7D",
                    raw_attrs=['target="_blank"'],
                )
                vuetify.VBtn(
                    "Profiles",
                    href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/../../share/opi/ADnEDv3/ADnED_XYProfileCursor.bob&macros=%7B%26quot%3BDET%26quot%3B%3A%26quot%3B4%26quot%3B%2C%26quot%3BDETNAME%26quot%3B%3A%26quot%3BMain%20Detector%20(4x4)%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID140%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%7D",
                    raw_attrs=['target="_blank"'],
                )
                vuetify.VBtn("Clear Array & Counts", disabled=True)
                vuetify.VBtn("Reset ROI", disabled=True)
                vuetify.VLabel("ROI")
                PVInput("BL12:Det:N1:Det4:XY:ROI:1:MinValue_RBV", label="Min")
                PVInput("BL12:Det:N1:Det4:XY:ROI:1:MaxValue_RBV", label="Max")
                PVInput("BL12:Det:N1:Det4:XY:ROI:1:MeanValue_RBV", label="Mean")
                PVInput("BL12:Det:N1:Det4:XY:ROI:1:Total_RBV", label="Mean")
                PVInput("BL12:Det:N1:Det4:XY:ROI:1:Rate", append="e/s", label="Mean")
                PVInput("BL12:Det:N1:Det4:XY:ROI:1:Show", label="Show", type="checkbox")

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
