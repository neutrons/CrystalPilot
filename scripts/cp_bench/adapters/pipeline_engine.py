"""Real metrics engine: reuse the CrystalPilot live pipeline on time slices.

For each stop-time ``t`` it loads ``[0, t]`` with ``FilterByTimeStop`` into the
pipeline's workspace (``live_event_ws``) and runs the app's own phases
(``load_config → refine_ub → integrate_and_predict → check_peaks``) — so the
metrics match the Live Data tab exactly. The engine's ``output_path`` is a
writable benchmark dir, and the pipeline's one ``/SNS``-writing call
(``MantidWorkflow.save_latest_ub`` → live-monitor dir) is neutralised per
instance so nothing under ``/SNS`` is ever modified.

Validated on the analysis server; unit tests use a fake ``ReductionEngine``.
"""

from __future__ import annotations

from typing import Any

from ..models import MetricPoint, ReductionConfig
from ..safety import safe_makedirs

_WS = "live_event_ws"
_INTERMEDIATE = (
    "live_event_ws",
    "live_event_ws_peak",
    "live_event_md_Qsample",
    "live_peaks_ws",
    "live_predict_peaks_ws",
)


def _no_save(*_args: Any, **_kwargs: Any) -> str:
    """Instance override for ``save_latest_ub`` — prevents any write under /SNS."""
    return ""


class PipelineReductionEngine:
    """Compute per-slice metrics by driving the app's live-reduction pipeline."""

    def __init__(self, selector: str = "Max Peak", point_group: str = "-1") -> None:
        self.selector = selector
        # StatisticsOfPeaksWorkspace (inside check_peaks) needs a point group;
        # ReduceSCD configs carry cell_type/centering but not always PG, so it
        # is an explicit input here (see CP_BENCH_PLAN §9). Default: triclinic.
        self.point_group = point_group

    def metrics_at(
        self,
        nxs_path: str,
        time_stop_s: float,
        cfg: ReductionConfig,
        out_dir: str,
    ) -> MetricPoint:
        """Reduce ``[0, time_stop_s]`` and return its quality metrics."""
        import mantid.simpleapi as mtdapi

        from exphub.core.beamline import set_active
        from exphub.techniques.single_crystal.models.temporal_analysis import (
            pipeline,
            workflow,
        )

        set_active("topaz")
        writable = safe_makedirs(out_dir)

        wf: Any = workflow.MantidWorkflow()
        # Neutralise the only pipeline call that writes under /SNS (wf is Any,
        # so this instance-level override is not a typed method assignment).
        wf.save_latest_ub = _no_save
        self._seed_workflow(wf, cfg, writable)

        try:
            mtdapi.LoadEventNexus(
                Filename=nxs_path,
                FilterByTimeStop=float(time_stop_s),
                OutputWorkspace=_WS,
            )
            run = mtdapi.mtd[_WS].getRun()
            wf.current_run = mtdapi.mtd[_WS].getRunNumber()
            wf.initial_run_start_time = run.startTime().totalNanoseconds() * 1e-9
            wf.current_run_start_time = wf.initial_run_start_time
            wf.update_peak_output_filenames()

            pipeline.load_config(wf)
            pipeline.refine_ub(wf)
            pipeline.integrate_and_predict(wf)
            pipeline.check_peaks(wf)

            point = self._collect(mtdapi, wf, time_stop_s)
        finally:
            self._cleanup(mtdapi)
        return point

    # ------------------------------------------------------------------ #
    def _seed_workflow(self, wf: Any, cfg: ReductionConfig, out_dir: str) -> None:
        """Populate the workflow attributes the pipeline phases read."""
        wf.calib_fname = cfg.get("calibration_file_1")
        wf.output_path = out_dir.rstrip("/") + "/"
        wf.min_d = cfg.get_float("min_d", 3.0)
        wf.max_d = cfg.get_float("max_d", 25.0)
        wf.tolerance = cfg.get_float("tolerance", 0.12)
        wf.cell_type = cfg.get_optional("cell_type")
        wf.centering = cfg.get("centering", "P") or "P"
        wf.point_group = cfg.get("point_group") or self.point_group
        wf.selection = self.selector

    def _collect(self, mtdapi: Any, wf: Any, time_stop_s: float) -> MetricPoint:
        """Assemble a :class:`MetricPoint` from the workflow + peak statistics."""
        point = MetricPoint(
            time_stop_s=float(time_stop_s),
            proton_charge=float(getattr(wf, "proton_charge", 0.0) or 0.0),
            num_peaks=int(getattr(wf, "sum", 0) or 0),
            sig2=int(getattr(wf, "sig2", 0) or 0),
            sig3=int(getattr(wf, "sig3", 0) or 0),
            sig5=int(getattr(wf, "sig5", 0) or 0),
            sig10=int(getattr(wf, "sig10", 0) or 0),
            intensity_ratio=float(getattr(wf, "intensity_ratio", 0.0) or 0.0),
            rsig=float(getattr(wf, "Rsig", 0.0) or 0.0),
            lattice=dict(getattr(wf, "latest_lattice", {}) or {}),
        )
        try:
            _sorted, table, _equiv = mtdapi.StatisticsOfPeaksWorkspace(
                InputWorkspace="live_predict_peaks_ws",
                PointGroup=wf.point_group,
                LatticeCentering=wf.centering,
                SortBy="Overall",
                WeightedZScore=True,
            )
            stats = table.row(0)
            point.mean_i_over_sigma = float(stats.get("Mean ((I)/sd(I))", 0.0))
            point.num_unique_reflections = int(stats.get("No. of Unique Reflections", 0))
            point.multiplicity = float(stats.get("Multiplicity", 0.0))
            point.rmerge = float(stats.get("Rmerge", 0.0))
            point.rpim = float(stats.get("Rpim", 0.0))
        except Exception as exc:
            point.error = f"statistics failed: {exc}"
        return point

    def _cleanup(self, mtdapi: Any) -> None:
        """Delete intermediate workspaces so the time loop stays memory-bounded."""
        for name in _INTERMEDIATE:
            try:
                if mtdapi.mtd.doesExist(name):
                    mtdapi.DeleteWorkspace(name)
            except Exception:
                continue
