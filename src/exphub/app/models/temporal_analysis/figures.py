"""Pure figure builders for the live-data tab.

Each builder takes a slice of :class:`MantidWorkflow` series + the
prediction-model name and returns a fully laid-out plotly ``Figure``.
Functions are deliberately pure (no I/O, no module/class state) so they
can be reused across selection modes and dropped onto a unit test.

The caller (:class:`TemporalAnalysisModel`) decides which series to feed
in based on the active prediction model and peak-selection mode.
"""

from __future__ import annotations

from typing import Any, List, Optional

import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

from ._debug import trace

FIG_MARGIN = {"l": 50, "r": 15, "t": 35, "b": 40}
GRID_KWARGS = {
    "showgrid": True,
    "gridcolor": "rgba(120,120,120,0.35)",
    "gridwidth": 1,
    "griddash": "dot",
}


def _apply_axes(fig: go.Figure) -> None:
    fig.update_xaxes(showline=True, linewidth=2, linecolor="black", mirror=True, **GRID_KWARGS)
    fig.update_yaxes(showline=True, linewidth=2, linecolor="black", mirror=True, **GRID_KWARGS)


def _waiting_for_data(fig: go.Figure, title: str, yaxis_title: str) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        xaxis_title="Time Steps (s)",
        yaxis_title=yaxis_title,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=FIG_MARGIN,
    )
    _apply_axes(fig)
    fig.add_annotation(
        text="Waiting for data",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 20, "color": "red"},
    )
    return fig


def build_intensity_figure(
    time_steps: List[float],
    intensity_data: Any,
    model_type: str,
) -> go.Figure:
    """Top figure: intensity-ratio history + extrapolated prediction line."""
    fig = go.Figure()

    if model_type == "Linear Interpolation":
        title = "Prediction of Intensity"
        yaxis = "Intensity"
    else:
        title = "Prediction of Signal Noise Ratio"
        yaxis = "Signal Noise Ratio"

    if len(time_steps) > 0:
        print("============================================================================================")
        trace("time_steps")
        trace(time_steps)
        trace("intensity_data")
        trace(intensity_data)
        print("============================================================================================")

        x = np.array(time_steps).reshape(-1, 1) ** 0.5
        y = np.array(intensity_data)

        model = LinearRegression()
        model.fit(x, y)
        slope = model.coef_[0]
        intercept = model.intercept_
        trace(f"Slope: {slope}, Intercept: {intercept}")

        if model_type == "Linear Interpolation":
            x_range = np.linspace(max(time_steps), max(time_steps) + 2000, 100)
            y_range = np.zeros_like(x_range) + np.array(intensity_data)[-1]
        else:
            x_range = np.linspace(max(time_steps), max(time_steps) + 2000, 100)
            y_range = slope * x_range ** 0.5 + intercept

        fig.add_trace(
            go.Scatter(x=x_range, y=y_range, mode="lines", name="Prediction Line", line={"dash": "dash"})
        )
        fig.add_trace(
            go.Scatter(x=time_steps, y=intensity_data, mode="lines+markers", name="History Data")
        )
        fig.update_layout(
            title={"text": title, "x": 0.5, "xanchor": "center"},
            xaxis_title="Time Steps (s)",
            yaxis_title=yaxis,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=FIG_MARGIN,
        )
        _apply_axes(fig)
    else:
        _waiting_for_data(fig, title, yaxis)
    return fig


def build_uncertainty_figure(
    time_steps: List[float],
    uncertainty_data: Any,
    model_type: str,
    guard_series: Optional[List[float]] = None,
) -> go.Figure:
    """Bottom figure: σ(I)/I (Rsig) history + fitted prediction curve.

    Note: the legacy build guarded plotting on ``len(measure_times)``
    regardless of the active series; ``guard_series`` reproduces that
    behavior. Pass ``None`` to guard on ``time_steps`` directly.
    """
    fig = go.Figure()

    if model_type == "Linear Interpolation":
        title = "Prediction of Uncertainty"
        yaxis = "Uncertainty (%)"
        ts_arr = np.array(time_steps)
        un_arr = np.array(uncertainty_data)
        nozero_mask = np.where(ts_arr > 0)
        x_pre = np.array(ts_arr[nozero_mask]).reshape(-1, 1)
        y_pre = np.array(un_arr[nozero_mask])
        x_transformed_pre = 1 / x_pre ** 0.5
        trace("X_transformed")
        trace(x_transformed_pre)
        trace("y")
        trace(y_pre)
        model_pre = LinearRegression()
        model_pre.fit(x_transformed_pre, y_pre)
        trace(f"Slope: {model_pre.coef_[0]}, Intercept: {model_pre.intercept_}")
    else:
        title = "Prediction of σ(I)/I"
        yaxis = "σ(I)/I (%)"

    guard = guard_series if guard_series is not None else time_steps
    if len(guard) > 0:
        un_arr = np.array(uncertainty_data)
        ts_arr = np.array(time_steps)
        x = np.array(ts_arr).reshape(-1, 1)
        y = np.array(un_arr) ** -1
        x_transformed = x ** 0.5
        trace("X_transformed")
        trace(x_transformed)
        trace("y")
        trace(y)

        model = LinearRegression()
        model.fit(x_transformed, y)
        slope = model.coef_[0]
        intercept = model.intercept_
        trace(f"Slope: {slope}, Intercept: {intercept}")

        x_range = np.linspace(max(ts_arr), max(ts_arr) + 2000, 100)
        y_range = (slope * (x_range ** 0.5) + intercept) ** -1

        fig.add_trace(
            go.Scatter(x=x_range, y=y_range, mode="lines", name="Fitted Line", line={"dash": "dash"})
        )
        print("============================================================================================")
        trace("time_steps")
        trace(ts_arr)
        trace("uncertainty_data")
        trace(un_arr)
        print("============================================================================================")
        fig.add_trace(go.Scatter(x=ts_arr, y=un_arr, mode="lines+markers", name="Uncertainty Data"))
        fig.update_layout(
            title={"text": title, "x": 0.5, "xanchor": "center"},
            xaxis_title="Time Steps (s)",
            yaxis_title=yaxis,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=FIG_MARGIN,
        )
        _apply_axes(fig)
    else:
        _waiting_for_data(fig, title, yaxis)
    return fig
