"""Tests for the metrics-vs-time grids and orchestration (fake engine)."""

from __future__ import annotations

from typing import Callable

import pytest

from scripts.cp_bench.metrics import (
    ReductionEngine,
    compute_metrics_vs_time,
    linear_time_grid,
    log_time_grid,
    make_time_grid,
)
from scripts.cp_bench.models import MetricPoint, ReductionConfig, RunInfo

EngineFactory = Callable[[Callable[[float], MetricPoint]], ReductionEngine]


def test_linear_time_grid() -> None:
    assert linear_time_grid(500.0, 5) == [100.0, 200.0, 300.0, 400.0, 500.0]
    assert linear_time_grid(0.0, 5) == []
    assert linear_time_grid(500.0, 0) == []


def test_log_time_grid_monotonic_ends_at_total() -> None:
    grid = log_time_grid(6000.0, 5, start_s=60.0)
    assert grid[0] == pytest.approx(60.0)
    assert grid[-1] == 6000.0
    assert grid == sorted(grid)
    assert len(grid) <= 6
    # Short run collapses to a single window.
    assert log_time_grid(30.0, 5, start_s=60.0) == [30.0]


def test_make_time_grid_dispatch() -> None:
    assert make_time_grid(500.0, 5, "linear") == linear_time_grid(500.0, 5)
    assert make_time_grid(6000.0, 5, "log") == log_time_grid(6000.0, 5)
    with pytest.raises(ValueError, match="unknown time-grid kind"):
        make_time_grid(1.0, 1, "bogus")


def test_compute_metrics_vs_time(fake_engine_factory: EngineFactory) -> None:
    engine = fake_engine_factory(lambda t: MetricPoint(time_stop_s=t, sig3=int(t)))
    run = RunInfo(run_number=1, nxs_path="/SNS/TOPAZ/IPTS-1/nexus/TOPAZ_1.nxs.h5", duration_s=300.0)
    cfg = ReductionConfig(source_path="mem")
    grid = [100.0, 200.0, 300.0]
    points = compute_metrics_vs_time(run, cfg, engine, grid, "/tmp/out")
    assert [p.time_stop_s for p in points] == grid
    assert [p.sig3 for p in points] == [100, 200, 300]


def test_compute_metrics_captures_slice_error(fake_engine_factory: EngineFactory) -> None:
    def maker(t: float) -> MetricPoint:
        if t == 200.0:
            raise RuntimeError("boom")
        return MetricPoint(time_stop_s=t)

    engine = fake_engine_factory(maker)
    run = RunInfo(run_number=1, nxs_path="x")
    points = compute_metrics_vs_time(run, ReductionConfig(source_path="mem"), engine, [100.0, 200.0, 300.0], "/tmp/o")
    assert points[1].error == "boom"
    assert points[0].error == ""
    # A failed slice does not abort the series.
    assert len(points) == 3
