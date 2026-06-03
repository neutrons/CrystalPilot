"""TOPAZ-specific Instrument Status (CSS) tab.

Holds the ADnED 4×4 detector + TOF channel layout and the BL12 PV wiring.
Moved here from ``app/views/css_status.py`` as part of the multi-beamline
refactor (see MULTI_BEAMLINE_PLAN.md, Phase 4).
"""

import time
from math import ceil
from typing import Any, Optional

import numpy as np
import plotly.graph_objects as go
from nova.epics.trame import DisconnectedAlert, PVInput, PVPlot
from nova.trame.view.components import InputField
from nova.trame.view.layouts import GridLayout, HBoxLayout, VBoxLayout
from trame.app import get_server
from trame.widgets import client, plotly
from trame.widgets import vuetify3 as vuetify
from trame_client.widgets.core import AbstractElement

from ....techniques.single_crystal.view_models.steering import SingleCrystalSteeringViewModel


class _GatedPVPlot:
    """Drop-in replacement for ``nova.epics.trame.PVPlot`` that fixes a bad fan-out.

    The vendored ``PVPlot`` registers ``server.state.change("epics")`` for *every*
    plot, so a single PV update fans out to all plots in the app. With ~30 active
    PVs each ticking at ~1 Hz, the original code triggers ~30 × N_plots figure
    pushes per second over the websocket — even when most plots' own PVs haven't
    changed. The browser plus the asyncio event loop get swamped, which is what
    makes unrelated UI actions (e.g. picking a goniometer) feel frozen.

    This subclass:
      1. Wraps the on_pv_change callback so it short-circuits when *this* plot's
         PV value object hasn't changed (identity check, fast).
      2. Throttles re-render of any single plot to at most 4 Hz.
      3. Caches the last go.Figure and skips figure.update() if identical.

    Subclasses provide ``_build_figure()`` which returns a fully-styled go.Figure.
    """

    _MIN_RENDER_INTERVAL_S = 0.25

    def __init__(self, pv_name: str, data_width: Optional[int] = None, **kwargs: Any) -> None:
        self.server = get_server(None, client_type="vue3")
        self.pv_name = pv_name
        self.data_width = data_width
        self.display_type = "heatmap" if data_width is not None else "line"
        self.instrument_id = pv_name.split(":")[0]
        self._last_raw: Any = None
        self._last_figure: Optional[go.Figure] = None
        self._last_render_t: float = 0.0

        with VBoxLayout(
            v_if=(
                f"'{self.instrument_id}:Det:Neutrons' in epics.pv_data && "
                f"epics.pv_data['{self.instrument_id}:Det:Neutrons'] > 0 && "
                f"'{pv_name}' in epics.pv_data && "
                f"epics.pv_data['{pv_name}']"
            ),
            classes="border-md position-relative",
            stretch=True,
        ):
            figure_widget = plotly.Figure(**kwargs)
            DisconnectedAlert()

            @self.server.state.change("epics")
            def on_pv_change(*args: Any, **kwargs: Any) -> None:
                try:
                    raw = self.server.state.epics["pv_data"].get(self.pv_name)
                except Exception:
                    return
                # Gate 1: this plot's PV value didn't change at all. Skip everything.
                if raw is self._last_raw and self._last_figure is not None:
                    return
                # Gate 2: throttle to at most one render every _MIN_RENDER_INTERVAL_S.
                now = time.time()
                if self._last_figure is not None and (now - self._last_render_t) < self._MIN_RENDER_INTERVAL_S:
                    return
                fig = self._build_figure()
                # Gate 3: only push if the rebuilt figure differs from the last push.
                if fig is None or fig is self._last_figure:
                    return
                figure_widget.update(fig)
                self._last_raw = raw
                self._last_figure = fig
                self._last_render_t = now

        with VBoxLayout(
            v_else=True, classes="border-md position-relative", halign="center", valign="center", stretch=True
        ):
            vuetify.VListSubheader("No Data")
            DisconnectedAlert()

    # Inherit the helpers from PVPlot for sub-class use:
    render_linechart = PVPlot.render_linechart
    render_heatmap = PVPlot.render_heatmap
    # `render_figure` from PVPlot is bypassed; subclasses override `_build_figure`.

    def _build_figure(self) -> go.Figure:  # subclass hook
        raise NotImplementedError


def _pv_string_expr(pv_name: str) -> str:
    """Return a Vue expression that yields a readable string for an EPICS char-array PV.

    EPICS string-waveform PVs (>40 chars) come through pvws as numeric arrays
    of char codes — Vuetify renders those as ``65,80,80,...``. Decode back to
    a UTF-8 string at the JS layer so titles, sample names, scan status, etc.
    display as plain text.
    """
    key = f"epics.pv_data['{pv_name}']"
    return (
        f"(Array.isArray({key}) "
        f"? String.fromCharCode.apply(null, {key}.filter(c => c)) "
        f": ({key} ?? ''))"
    )


class PVStringInput(InputField):
    """Read-only InputField that decodes char-array string PVs to plain text."""

    def __new__(cls, pv_name: str, **kwargs: Any) -> AbstractElement:
        kwargs.setdefault("readonly", True)
        return super().__new__(
            cls,
            model_value=(_pv_string_expr(pv_name),),
            **kwargs,
        )


class LinePVPlot(_GatedPVPlot):
    """1D spectra view with labeled axes/ticks/gridlines."""

    def __init__(
        self,
        pv_name: str,
        xaxis_title: str = "",
        yaxis_title: str = "Counts",
        **kwargs: Any,
    ) -> None:
        self._x_title = xaxis_title
        self._y_title = yaxis_title
        super().__init__(pv_name, **kwargs)

    def _build_figure(self) -> go.Figure:
        trace = self.render_linechart()
        if trace is None:
            return go.Figure()
        figure = go.Figure(trace)
        figure.update_layout(
            margin={"l": 55, "r": 10, "t": 10, "b": 40},
            xaxis={
                "visible": True,
                "title": self._x_title,
                "showgrid": True,
                "gridcolor": "rgba(120,120,120,0.3)",
                "showline": True,
                "linecolor": "black",
            },
            yaxis={
                "visible": True,
                "title": self._y_title,
                "showgrid": True,
                "gridcolor": "rgba(120,120,120,0.3)",
                "showline": True,
                "linecolor": "black",
            },
        )
        return figure


class LogPVPlot(_GatedPVPlot):
    """2D detector heatmap on a log color scale, with pixel-accurate aspect ratio.

    Replaces ``PVPlot``'s linear heatmap so weak features stay visible alongside
    the bright pixels of the TOPAZ 4×4 main detector.
    """

    def _render_log_heatmap(self) -> Optional[go.Heatmap]:
        if self.data_width is None:
            return None
        try:
            data = np.array(self.server.state.epics["pv_data"][self.pv_name])
            if data.ndim == 0:
                return None
        except Exception:
            return None
        rows = ceil(len(data) / self.data_width)
        cols = self.data_width
        log_data = np.log10(np.maximum(np.resize(data, (rows, cols)).astype(float), 0.0) + 1.0)
        return go.Heatmap(
            x=list(range(rows)),
            y=list(reversed(range(cols))),
            z=log_data.tolist(),
            colorscale="Viridis",
            showscale=False,
            zmin=float(log_data.min()),
            zmax=float(log_data.max()),
        )

    def _build_figure(self) -> go.Figure:
        trace = self._render_log_heatmap()
        if trace is None:
            return go.Figure()
        figure = go.Figure(trace)
        # Hide axes (parent default) but lock yaxis to xaxis so one detector
        # pixel renders as a square — the figure's aspect ratio then equals
        # the detector's cols/rows pixel ratio.
        figure.update_layout(
            margin={"b": 0, "l": 0, "r": 0, "t": 0},
            xaxis={"visible": False},
            yaxis={"visible": False, "scaleanchor": "x", "scaleratio": 1},
        )
        return figure


class CSSStatusView:
    """View class for Plotly."""

    def __init__(self, view_model: SingleCrystalSteeringViewModel) -> None:
        self.view_model = view_model
        self.view_model.cssstatus_bind.connect("model_cssstatus")
        self.create_ui()
        self.view_model.update_cssstatus_figure()

    def create_ui(self) -> None:
        with VBoxLayout(classes="border-md mb-1 px-2 py-1", stretch=True):
            # Give the 2D detector plenty of vertical space; scaleanchor on the
            # heatmap will then center it with the correct pixel aspect ratio.
            # Roughly 2x the previous 60vh share of the page to make the heatmap
            # the dominant element on this tab.
            with VBoxLayout(stretch=True, height="85vh"):
                LogPVPlot("BL12:Det:N1:Det4:XY:Array:ArrayData", data_range=[0, 32000], data_width=1105)

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

                with VBoxLayout(v_if="model_cssstatus.active_details_plot == 0", stretch=True):
                    with HBoxLayout(stretch=True):
                        LinePVPlot(
                            "BL12:Det:N1:Det1:TOF:Array:ArrayData",
                            xaxis_title="Time of Flight (bin)",
                            yaxis_title="Counts",
                        )

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
                with VBoxLayout(v_if="model_cssstatus.active_details_plot == 1", stretch=True):
                    with HBoxLayout(stretch=True):
                        LinePVPlot(
                            "BL12:Det:N1:Det2:TOF:Array:ArrayData",
                            xaxis_title="d-Space (Å)",
                            yaxis_title="Counts",
                        )

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
                with VBoxLayout(v_if="model_cssstatus.active_details_plot == 2", stretch=True):
                    with HBoxLayout(stretch=True):
                        LinePVPlot(
                            "BL12:Det:N1:Det3:TOF:Array:ArrayData",
                            xaxis_title="q-Space (Å⁻¹)",
                            yaxis_title="Counts",
                        )

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
                with VBoxLayout(v_if="model_cssstatus.active_details_plot == 3", stretch=True):
                    with HBoxLayout(stretch=True):
                        LinePVPlot(
                            "BL12:Det:N1:Det4:TOF:Array:ArrayData",
                            xaxis_title="d-Space (Å) — ROI filtered",
                            yaxis_title="Counts",
                        )

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
                with VBoxLayout(v_if="model_cssstatus.active_details_plot == 4", stretch=True):
                    with HBoxLayout(stretch=True):
                        LinePVPlot(
                            "BL12:Det:N1:Det5:TOF:Array:ArrayData",
                            xaxis_title="q-Space (Å⁻¹) — ROI filtered",
                            yaxis_title="Counts",
                        )

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
                # ── BL12 User Info — mirrors webopi.sns.gov/bl12/.../BL12_User.bob ──
                with VBoxLayout(classes="border-md pa-1"):
                    vuetify.VLabel("Proposal", style="font-weight: 600; padding-left: 4px;")
                    with GridLayout(columns=2, gap="0.25em"):
                        PVInput("BL12:CS:IPTS", label="IPTS")
                        PVInput("BL12:CS:RunControl:LastRunNumber", label="Run")
                        PVInput("BL12:CS:RunControl:StateEnum", label="State")
                        PVInput("BL12:CS:ITEMS", label="Sample ID")
                        PVStringInput("BL12:CS:IPTS:Title", label="Proposal Title")
                        PVStringInput("BL12:CS:ITEMS:Name", label="Sample")
                        PVStringInput("BL12:SMS:RunInfo:RunTitle", label="Run Title")
                        PVStringInput("BL12:AR:Sequence:Name", label="Notes")

                with VBoxLayout(classes="border-md pa-1"):
                    vuetify.VLabel("Neutrons", style="font-weight: 600; padding-left: 4px;")
                    with GridLayout(columns=2, gap="0.25em"):
                        PVInput("BL12:Det:Neutrons", label="Total Counts")
                        PVInput("BL12:Det:N1:Det1:EventRate_RBV", append="e/s", label="Counts/sec")
                        PVInput("BL12:Det:PCharge:C", append="C", label="Proton Charge")
                        PVInput("BL12:Det:rtdl:BeamPowerAvg", append="MW", label="Beam Power")
                        PVInput("BL12:Det:TH:BL:Frequency", append="Hz", label="Frame Rate")
                        PVInput("BL12:Det:TH:BL:Lambda", append="Å", label="Wavelength")
                        PVInput("PPS_BMLN:BL12:ShtrOpen", label="Shutters Open")

                with VBoxLayout(classes="border-md pa-1"):
                    vuetify.VLabel("Experiment Control", style="font-weight: 600; padding-left: 4px;")
                    with GridLayout(columns=2, gap="0.25em"):
                        PVInput("BL12:CS:Scan:Active", label="Scan Active")
                        PVStringInput("BL12:CS:Scan:Status", label="Scan Status")
                        PVInput("BL12:CS:Scan:Progress", label="Progress")
                        PVInput("BL12:CS:Scan:Finish", label="Finish")
                        PVInput("BL12:CS:Scan:State", label="Scan State")
                        PVInput("BL12:CS:RunControl:Running", label="Running")
                        PVInput("BL12:CS:RunControl:RunTimer", label="Run Timer")
                        PVInput("BL12:Det:N1:DetectorState_RBV", label="Data Collection State")
                        InputField(
                            model_value=("epics.pv_data['BL12:CS:RunControl:Pause'] ? 'Paused' : 'Not Paused'",),
                            label="Pause",
                        )
                        PVInput("BL12:CS:Scan:Alarm", label="Scan Alarm")
