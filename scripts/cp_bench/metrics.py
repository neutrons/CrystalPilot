"""Phase 2 — quality metrics vs elapsed time (deterministic time slicing).

The time axis is realised with ``LoadEventNexus(FilterByTimeStop=t)`` (as in
Mantid's ``stats_vs_time.py``), *not* the real-time live listener — so slices
are exact and repeatable. Per slice the app's own reduction pipeline is run and
its quality metrics captured, giving parity with the Live Data tab.

This module owns only the deterministic orchestration (grids + iteration); the
Mantid work is delegated to an injected :class:`ReductionEngine`.
"""

from __future__ import annotations

from typing import List, Protocol, Sequence

from .models import MetricPoint, ReductionConfig, RunInfo

#: The first (smallest) window used by the logarithmic grid, in seconds.
_LOG_GRID_START_S = 60.0


class ReductionEngine(Protocol):
    """Reduce the ``[0, time_stop_s]`` window of a run and return its metrics."""

    def metrics_at(
        self,
        nxs_path: str,
        time_stop_s: float,
        cfg: ReductionConfig,
        out_dir: str,
    ) -> MetricPoint:
        """Load the time-limited window, run the pipeline, return a metric point."""
        ...


def linear_time_grid(total_s: float, n_steps: int) -> List[float]:
    """Return ``n_steps`` evenly spaced stop-times in ``(0, total_s]``."""
    if total_s <= 0 or n_steps <= 0:
        return []
    step = total_s / n_steps
    grid = [round(step * (i + 1), 6) for i in range(n_steps)]
    grid[-1] = total_s
    return grid


def log_time_grid(total_s: float, n_steps: int, start_s: float = _LOG_GRID_START_S) -> List[float]:
    """Return up to ``n_steps`` geometrically spaced stop-times ending at ``total_s``.

    Mirrors ``stats_vs_time.py``'s ``60 * base**i`` progression: small early
    windows (where quality changes fastest) and coarser later ones. Values are
    de-duplicated and clamped to ``total_s``.
    """
    if total_s <= 0 or n_steps <= 0:
        return []
    if n_steps == 1 or total_s <= start_s:
        return [total_s]
    base = (total_s / start_s) ** (1.0 / (n_steps - 1))
    grid: List[float] = []
    for i in range(n_steps):
        value = min(start_s * (base**i), total_s)
        value = round(value, 6)
        if not grid or value > grid[-1]:
            grid.append(value)
    if grid[-1] != total_s:
        grid.append(total_s)
    return grid


def make_time_grid(total_s: float, n_steps: int, kind: str = "log") -> List[float]:
    """Dispatch to the linear or logarithmic grid builder."""
    if kind == "linear":
        return linear_time_grid(total_s, n_steps)
    if kind == "log":
        return log_time_grid(total_s, n_steps)
    raise ValueError(f"unknown time-grid kind {kind!r}; use 'log' or 'linear'")


def compute_metrics_vs_time(
    run: RunInfo,
    cfg: ReductionConfig,
    engine: ReductionEngine,
    grid: Sequence[float],
    out_dir: str,
) -> List[MetricPoint]:
    """Run the engine at each stop-time; a failed slice is recorded, not fatal."""
    points: List[MetricPoint] = []
    for time_stop in grid:
        try:
            point = engine.metrics_at(run.nxs_path, float(time_stop), cfg, out_dir)
        except Exception as exc:
            point = MetricPoint(time_stop_s=float(time_stop), error=str(exc))
        points.append(point)
    return points
