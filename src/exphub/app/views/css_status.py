"""Module for the CSS Status tab."""

from typing import Any

from nova.trame.view.components import InputField
from nova.trame.view.layouts import GridLayout, HBoxLayout, VBoxLayout
from trame.widgets import client, plotly
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

        return super().__new__(cls, v_model=f"model_cssstatus.pv_data['{pv_name}']", readonly=readonly, **kwargs)


class PVPlot:
    """Creates a plotly-based figure for the PV data object."""

    def __init__(self, pv_name: str, **kwargs: Any) -> None:
        with VBoxLayout(
            v_if=(
                "'BL12:Det:Neutrons' in model_cssstatus.pv_data && "
                "model_cssstatus.pv_data['BL12:Det:Neutrons'] > 0 && "
                f"'{pv_name}' in model_cssstatus.pv_data && "
                f"model_cssstatus.pv_data['{pv_name}']"
            ),
            classes="border-md",
            stretch=True,
        ):
            # TODO: need to inject go.Figure here with test data from Zhongcan.
            plotly.Figure(**kwargs)
        with VBoxLayout(v_else=True, classes="border-md", halign="center", valign="center", stretch=True):
            vuetify.VListSubheader("No Data")


class CSSStatusView:
    """View class for Plotly."""

    def __init__(self, view_model: MainViewModel) -> None:
        self.view_model = view_model
        self.view_model.cssstatus_bind.connect("model_cssstatus")
        self.create_ui()
        self.view_model.update_cssstatus_figure()

    def create_ui(self) -> None:
        with VBoxLayout(classes="border-md mb-1 px-2 py-1", stretch=True):
            with VBoxLayout(stretch=True):
                PVPlot("BL12:Det:N1:Det4:XY:Array:ArrayData")

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
                with client.DeepReactive("model_cssstatus"):
                    with vuetify.VTabs(v_model="model_cssstatus.active_details_plot"):
                        vuetify.VTab("TOF (All Modules)", value=0)
                        vuetify.VTab("d-Space (All Modules)", value=1)
                        vuetify.VTab("q-Space (All Modules)", value=2)
                        vuetify.VTab("d-Space (ROI Filtered)", value=3)
                        vuetify.VTab("q-Space (ROI Filtered)", value=4)

                with VBoxLayout(v_show="model_cssstatus.active_details_plot == 0", stretch=True):
                    with HBoxLayout(stretch=True):
                        PVPlot("BL12:Det:N1:Det1:TOF:Array:ArrayData")

                    with HBoxLayout(gap="0.25em", valign="center"):
                        vuetify.VLabel("ROI")
                        PVInput("BL12:Det:N1:Det1:TOF:ROI:1:Min", label="Start")
                        PVInput("BL12:Det:N1:Det1:TOF:ROI:1:Size", label="Size")
                        PVInput("BL12:Det:N1:Det1:TOF:ROI:1:MinValue_RBV", label="Min")
                        PVInput("BL12:Det:N1:Det1:TOF:ROI:1:MaxValue_RBV", label="Max")
                        PVInput("BL12:Det:N1:Det1:TOF:ROI:1:MeanValue_RBV", label="Mean")
                        PVInput("BL12:Det:N1:Det1:TOF:ROI:1:Total_RBV", label="Total")
                        vuetify.VBtn(
                            "More Detail",
                            href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/../../share/opi/ADnEDv3/ADnED_TOFArray.bob&macros=%7B%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID154%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BAXIS_TITLE%26quot%3B%3A%26quot%3BTime%20Of%20Flight%20(ms)%26quot%3B%2C%26quot%3BDET%26quot%3B%3A%26quot%3B1%26quot%3B%2C%26quot%3BDETNAME%26quot%3B%3A%26quot%3BMain%20TOF%26quot%3B%2C%26quot%3BNAME%26quot%3B%3A%26quot%3BTime%20Of%20Flight%20(All%20Modules)%26quot%3B%7D",
                            target="_blank",
                        )
                with VBoxLayout(v_show="model_cssstatus.active_details_plot == 1", stretch=True):
                    with HBoxLayout(stretch=True):
                        PVPlot("BL12:Det:N1:Det2:TOF:Array:ArrayData")

                    with HBoxLayout(gap="0.25em", valign="center"):
                        vuetify.VLabel("ROI")
                        PVInput("BL12:Det:N1:Det2:TOF:ROI:1:Min", label="Start")
                        PVInput("BL12:Det:N1:Det2:TOF:ROI:1:Size", label="Size")
                        PVInput("BL12:Det:N1:Det2:TOF:ROI:1:MinValue_RBV", label="Min")
                        PVInput("BL12:Det:N1:Det2:TOF:ROI:1:MaxValue_RBV", label="Max")
                        PVInput("BL12:Det:N1:Det2:TOF:ROI:1:MeanValue_RBV", label="Mean")
                        PVInput("BL12:Det:N1:Det2:TOF:ROI:1:Total_RBV", label="Total")
                        vuetify.VBtn(
                            "More Detail",
                            href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/../../share/opi/ADnEDv3/ADnED_TOFArray.bob&macros=%7B%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID154%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BAXIS_TITLE%26quot%3B%3A%26quot%3Bd-Space%20(A)%26quot%3B%2C%26quot%3BDET%26quot%3B%3A%26quot%3B2%26quot%3B%2C%26quot%3BDETNAME%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BNAME%26quot%3B%3A%26quot%3Bd-Space%20(All%20Modules)%26quot%3B%7D",
                            target="_blank",
                        )
                with VBoxLayout(v_show="model_cssstatus.active_details_plot == 2", stretch=True):
                    with HBoxLayout(stretch=True):
                        PVPlot("BL12:Det:N1:Det3:TOF:Array:ArrayData")

                    with HBoxLayout(gap="0.25em", valign="center"):
                        vuetify.VLabel("ROI")
                        PVInput("BL12:Det:N1:Det3:TOF:ROI:1:Min", label="Start")
                        PVInput("BL12:Det:N1:Det3:TOF:ROI:1:Size", label="Size")
                        PVInput("BL12:Det:N1:Det3:TOF:ROI:1:MinValue_RBV", label="Min")
                        PVInput("BL12:Det:N1:Det3:TOF:ROI:1:MaxValue_RBV", label="Max")
                        PVInput("BL12:Det:N1:Det3:TOF:ROI:1:MeanValue_RBV", label="Mean")
                        PVInput("BL12:Det:N1:Det3:TOF:ROI:1:Total_RBV", label="Total")
                        vuetify.VBtn(
                            "More Detail",
                            href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/../../share/opi/ADnEDv3/ADnED_TOFArray.bob&macros=%7B%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID154%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BAXIS_TITLE%26quot%3B%3A%26quot%3Bq-Space%26quot%3B%2C%26quot%3BDET%26quot%3B%3A%26quot%3B3%26quot%3B%2C%26quot%3BDETNAME%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BNAME%26quot%3B%3A%26quot%3Bq-Space%20(All%20Modules)%26quot%3B%7D",
                            target="_blank",
                        )
                with VBoxLayout(v_show="model_cssstatus.active_details_plot == 3", stretch=True):
                    with HBoxLayout(stretch=True):
                        PVPlot("BL12:Det:N1:Det4:TOF:Array:ArrayData")

                    with HBoxLayout(gap="0.25em", valign="center"):
                        vuetify.VLabel("ROI")
                        PVInput("BL12:Det:N1:Det4:TOF:ROI:1:Min", label="Start")
                        PVInput("BL12:Det:N1:Det4:TOF:ROI:1:Size", label="Size")
                        PVInput("BL12:Det:N1:Det4:TOF:ROI:1:MinValue_RBV", label="Min")
                        PVInput("BL12:Det:N1:Det4:TOF:ROI:1:MaxValue_RBV", label="Max")
                        PVInput("BL12:Det:N1:Det4:TOF:ROI:1:MeanValue_RBV", label="Mean")
                        PVInput("BL12:Det:N1:Det4:TOF:ROI:1:Total_RBV", label="Total")
                        vuetify.VBtn(
                            "More Detail",
                            href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/../../share/opi/ADnEDv3/ADnED_TOFArray.bob&macros=%7B%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID318%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BAXIS_TITLE%26quot%3B%3A%26quot%3Bd-Space%20(A)%26quot%3B%2C%26quot%3BDET%26quot%3B%3A%26quot%3B4%26quot%3B%2C%26quot%3BDETNAME%26quot%3B%3A%26quot%3BROI%20d-Space%26quot%3B%2C%26quot%3BNAME%26quot%3B%3A%26quot%3BROI%20d-Space%20(filtered%20based%20on%202D%20ROI)%26quot%3B%7D",
                            target="_blank",
                        )
                with VBoxLayout(v_show="model_cssstatus.active_details_plot == 4", stretch=True):
                    with HBoxLayout(stretch=True):
                        PVPlot("BL12:Det:N1:Det5:TOF:Array:ArrayData")

                    with HBoxLayout(gap="0.25em", valign="center"):
                        vuetify.VLabel("ROI")
                        PVInput("BL12:Det:N1:Det5:TOF:ROI:1:Min", label="Start")
                        PVInput("BL12:Det:N1:Det5:TOF:ROI:1:Size", label="Size")
                        PVInput("BL12:Det:N1:Det5:TOF:ROI:1:MinValue_RBV", label="Min")
                        PVInput("BL12:Det:N1:Det5:TOF:ROI:1:MaxValue_RBV", label="Max")
                        PVInput("BL12:Det:N1:Det5:TOF:ROI:1:MeanValue_RBV", label="Mean")
                        PVInput("BL12:Det:N1:Det5:TOF:ROI:1:Total_RBV", label="Total")
                        vuetify.VBtn(
                            "More Detail",
                            href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/../../share/opi/ADnEDv3/ADnED_TOFArray.bob&macros=%7B%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID154%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BAXIS_TITLE%26quot%3B%3A%26quot%3Bd-Space%20(A)%26quot%3B%2C%26quot%3BDET%26quot%3B%3A%26quot%3B4%26quot%3B%2C%26quot%3BDETNAME%26quot%3B%3A%26quot%3BROI%20d-Space%26quot%3B%2C%26quot%3BNAME%26quot%3B%3A%26quot%3BROI%20d-Space%20(filtered%20based%20on%202D%20ROI)%26quot%3B%7D",
                            target="_blank",
                        )

            with VBoxLayout(stretch=True):
                with VBoxLayout(classes="border-md pa-1", stretch=True):
                    PVPlot("BL12:Det:Cursor4x4:Info")
                    vuetify.VBtn(
                        "Cursor Detail",
                        href="https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/../../share/opi/ADnEDv3/ADnED_TOFArray.bob&macros=%7B%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID154%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BAXIS_TITLE%26quot%3B%3A%26quot%3Bq-Space%26quot%3B%2C%26quot%3BDET%26quot%3B%3A%26quot%3B5%26quot%3B%2C%26quot%3BDETNAME%26quot%3B%3A%26quot%3BROI%20q-Space%26quot%3B%2C%26quot%3BNAME%26quot%3B%3A%26quot%3BROI%20q-Space%20(filtered%20based%20on%202D%20ROI)%26quot%3B%7D",
                        raw_attrs=['target="_blank"'],
                    )

                with GridLayout(classes="border-md pa-1", columns=2):
                    PVInput("BL12:Det:N1:DetectorState_RBV", label="Data Collection State")
                    InputField(
                        model_value=("model_cssstatus.pv_data['BL12:Det:N1:Pause'] ? 'Paused' : 'Not Paused'",),
                        label="Pause",
                    )
                    PVInput("BL12:Det:Neutrons", label="Total Counts")
                    PVInput("BL12:Det:N1:Det1:EventRate_RBV", append="e/s", label="Counts/sec")
                    PVInput("BL12:Det:PCharge:C", append="C", label="Proton Charge")
                    PVInput("BL12:Det:rtdl:BeamPowerAvg", append="MW", label="Beam Power")
