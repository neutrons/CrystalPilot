"""Pydantic binding surface for the live-data tab.

Holds the per-cycle UI state (selection mode, prediction model, latest UB)
and exposes ``get_figure_intensity`` / ``get_figure_uncertainty`` for the
view. Figure construction itself lives in :mod:`.figures`; this class only
selects which series to feed each builder and memoises the result.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pydantic import BaseModel, Field

from .figures import build_intensity_figure, build_uncertainty_figure
from .workflow import MantidWorkflow


class TemporalAnalysisModel(BaseModel):
    """Pydantic class for holding temporal analysis information."""

    table_test: List[Dict] = Field(default=[{"title": "1", "header": "h"}])
    prediction_model_type: str = Field(default="Poisson Model", title="Prediction Model")
    prediction_model_type_options: List[str] = ["Poisson Model", "Bayesian Model", "Linear Interpolation"]
    data_selection: str = Field(default="All Peaks", title="Peak Selection")
    data_selection_options: List[str] = [
        "All Peaks",
        "Bragg Peaks",
        "Max Peak",
        "Satellite Peaks",
        "Diffuse scattering",
    ]
    time_steps: List[float] = Field(
        default=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0], title="Time Steps"
    )
    intensity_data: List[float] = Field(
        default=[0.0, 1.0, 4.0, 9.0, 16.0, 25.0, 36.0, 49.0, 64.0, 81.0], title="Intensity Data"
    )
    variance_data: List[float] = Field(
        default=[0.0, 0.1, 0.4, 0.9, 1.6, 2.5, 3.6, 4.9, 6.4, 8.1], title="Variance Data"
    )
    uncertainty_data: List[float] = Field(
        default=[0.0, 0.2, 0.6, 1.2, 2.0, 3.0, 4.2, 5.6, 7.2, 9.0], title="Uncertainty Data"
    )
    timestamp: float = Field(default=0.0, title="timestamp")
    all_time: List[float] = Field(default=[0.0, 10000], title="All Time")
    time_interval: float = Field(default=40, title="Time Interval")

    latest_ub: List[List[float]] = Field(
        default_factory=lambda: [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
        title="Latest UB",
        description="Most recent UB matrix inferred from live data (rows are UB rows).",
    )
    latest_ub_timestamp: str = Field(default="", title="Latest UB timestamp")
    latest_ub_saved_path: str = Field(default="", title="Latest UB saved path")
    latest_lattice: Dict[str, float] = Field(
        default_factory=lambda: {
            "a": 0.0,
            "b": 0.0,
            "c": 0.0,
            "alpha": 0.0,
            "beta": 0.0,
            "gamma": 0.0,
            "volume": 0.0,
        },
        title="Latest lattice constants (Å / deg / Å³)",
    )
    latest_lattice_summary: str = Field(
        default="",
        title="Latest lattice summary",
        description="Pretty one-line a,b,c,α,β,γ,V derived from latest_lattice.",
    )
    latest_ub_rows: List[Dict[str, Any]] = Field(
        default_factory=lambda: [
            {"row": "row 1", "c1": 0.0, "c2": 0.0, "c3": 0.0},
            {"row": "row 2", "c1": 0.0, "c2": 0.0, "c3": 0.0},
            {"row": "row 3", "c1": 0.0, "c2": 0.0, "c3": 0.0},
        ],
        title="Latest UB (table rows)",
    )
    latest_ub_headers: List[Dict[str, Any]] = Field(
        default_factory=lambda: [
            {"title": "", "value": "row", "sortable": False, "align": "center"},
            {"title": "col 1", "value": "c1", "sortable": False, "align": "center"},
            {"title": "col 2", "value": "c2", "sortable": False, "align": "center"},
            {"title": "col 3", "value": "c3", "sortable": False, "align": "center"},
        ],
    )

    # Created lazily by start_reading_live_mtd_data() once Mantid is ready.
    _mtd_workflow: Optional[MantidWorkflow] = None
    # Optional back-reference to MainModel; set by MainViewModel during wiring.
    _parent: Any = None
    # Figure builders are pure-but-expensive (each refits LinearRegression).
    # Cache by (model_type, len(series), tail values) so unchanged ticks reuse the figure.
    _intensity_fig_cache: Optional[tuple[Any, go.Figure]] = None
    _uncertainty_fig_cache: Optional[tuple[Any, go.Figure]] = None

    @property
    def mtd_workflow(self) -> Optional[MantidWorkflow]:
        """Return the MantidWorkflow instance, or None if not yet initialized."""
        return self._mtd_workflow

    def set_parent(self, parent: Any) -> None:
        """Set a back-reference to the owning MainModel."""
        from ..main_model import MainModel

        self._parent: MainModel = parent

    def get_models(self) -> Any:
        """Return the parent MainModel (or None) without importing it here."""
        try:
            print("try get models from parent")
            if getattr(self, "_parent", None) is not None:
                print("get models from parent")
                if self._parent:
                    print(self._parent.experimentinfo)
                return self._parent
        except Exception:
            return None
        return None

    def sync_latest_ub_from_workflow(self) -> None:
        """Copy latest UB / lattice from MantidWorkflow into pydantic fields.

        The workflow holds plain Python attributes; the side-table binds to
        these pydantic fields. Called after each live-data reduction tick.
        """
        if self._mtd_workflow is None:
            return
        ub = getattr(self._mtd_workflow, "latest_ub", None)
        if ub is None:
            return
        try:
            self.latest_ub = [[float(v) for v in row] for row in ub]
            self.latest_ub_timestamp = getattr(self._mtd_workflow, "latest_ub_timestamp", "") or ""
            self.latest_ub_saved_path = getattr(self._mtd_workflow, "latest_ub_saved_path", "") or ""
            self.latest_ub_rows = [
                {
                    "row": f"row {i + 1}",
                    "c1": round(self.latest_ub[i][0], 6),
                    "c2": round(self.latest_ub[i][1], 6),
                    "c3": round(self.latest_ub[i][2], 6),
                }
                for i in range(3)
            ]
            lat = getattr(self._mtd_workflow, "latest_lattice", None)
            if lat:
                self.latest_lattice = {k: float(v) for k, v in lat.items()}
                self.latest_lattice_summary = (
                    f"a = {lat['a']:.4f} Å    b = {lat['b']:.4f} Å    c = {lat['c']:.4f} Å    "
                    f"α = {lat['alpha']:.3f}°    β = {lat['beta']:.3f}°    γ = {lat['gamma']:.3f}°    "
                    f"V = {lat['volume']:.2f} Å³"
                )
        except Exception as e:
            print(f"sync_latest_ub_from_workflow: {e}")

    # ---------- series resolution + figure dispatch ----------

    def _series_for_intensity(self) -> tuple[Any, Any]:
        wf = self._mtd_workflow
        if self.prediction_model_type == "Poisson Model":
            return wf.measure_times, wf.intensity_ratios
        return wf.timeseries_plt, np.array(wf.timeseries_data_plt)

    def _series_for_uncertainty(self) -> tuple[Any, Any]:
        wf = self._mtd_workflow
        if self.prediction_model_type == "Poisson Model":
            return wf.measure_times, wf.rsigs
        return wf.timeseries_plt, wf.temporal_poisson_uncertainty

    def _intensity_cache_key(self) -> Any:
        if self._mtd_workflow is None:
            return ("none",)
        ts, vals = self._series_for_intensity()
        n = len(ts)
        return (
            self.prediction_model_type,
            n,
            ts[-1] if n else None,
            vals[-1] if n and len(vals) else None,
        )

    def get_figure_intensity(self) -> go.Figure:
        cache_key = self._intensity_cache_key()
        cached = self._intensity_fig_cache
        if cached is not None and cached[0] == cache_key:
            return cached[1]
        fig = self._build_figure_intensity()
        self._intensity_fig_cache = (cache_key, fig)
        return fig

    def _build_figure_intensity(self) -> go.Figure:
        if self._mtd_workflow is None:
            return go.Figure()
        ts, vals = self._series_for_intensity()
        return build_intensity_figure(ts, vals, self.prediction_model_type)

    def _uncertainty_cache_key(self) -> Any:
        if self._mtd_workflow is None:
            return ("none",)
        ts, vals = self._series_for_uncertainty()
        n = len(ts)
        return (
            self.prediction_model_type,
            n,
            ts[-1] if n else None,
            vals[-1] if n and len(vals) else None,
        )

    def get_figure_uncertainty(self) -> go.Figure:
        cache_key = self._uncertainty_cache_key()
        cached = self._uncertainty_fig_cache
        if cached is not None and cached[0] == cache_key:
            return cached[1]
        fig = self._build_figure_uncertainty()
        self._uncertainty_fig_cache = (cache_key, fig)
        return fig

    def _build_figure_uncertainty(self) -> go.Figure:
        if self._mtd_workflow is None:
            return go.Figure()
        ts, vals = self._series_for_uncertainty()
        # Legacy guard: uncertainty figure decided whether to plot based on
        # measure_times regardless of the active prediction-model series.
        # Preserved here for behavior parity with the pre-refactor code.
        guard_series = self._mtd_workflow.measure_times
        return build_uncertainty_figure(
            ts, vals, self.prediction_model_type, guard_series=guard_series
        )

    # ---------- live-data lifecycle (delegates to workflow) ----------

    def get_live_data(self) -> None:
        pass

    def generate_prediction_figure(self) -> go.Figure:
        return make_subplots(rows=1, cols=2)

    def stop_live_data(self) -> None:
        """Stop the Mantid MonitorLiveData thread if the workflow is running."""
        if self._mtd_workflow is not None:
            self._mtd_workflow.stop()

    def start_reading_live_mtd_data(self) -> None:
        if self._mtd_workflow is not None:
            self._mtd_workflow.stop()
        self._mtd_workflow = MantidWorkflow()
        models = self.get_models()
        if models is not None:
            self._mtd_workflow.update_experiment_info(models)
        self._mtd_workflow.start_live_data_collection_instances()
