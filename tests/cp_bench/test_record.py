"""Tests for the output layout, provenance, and serialisation helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.cp_bench.models import ComparisonResult, CutoffResult, MetricPoint
from scripts.cp_bench.record import (
    append_log,
    build_provenance,
    make_bench_paths,
    write_json,
    write_metrics_csv,
    write_summary,
)
from scripts.cp_bench.safety import ReadOnlyPathError


def test_make_bench_paths_creates_tree(tmp_path: Path) -> None:
    paths = make_bench_paths(str(tmp_path), ipts=1, run=100, timestamp="20260101-000000")
    for directory in (paths.discovery, paths.metrics, paths.reduction_full, paths.comparison):
        assert os.path.isdir(directory)
    assert paths.root.endswith(os.path.join("IPTS-1", "CP-bench", "100", "20260101-000000"))


def test_make_bench_paths_blocks_sns() -> None:
    with pytest.raises(ReadOnlyPathError):
        make_bench_paths("/SNS/TOPAZ", ipts=1, run=100, timestamp="t")


def test_write_json_and_metrics_csv(tmp_path: Path) -> None:
    jpath = write_json(str(tmp_path / "x.json"), {"b": 1, "a": 2})
    assert json.loads(Path(jpath).read_text()) == {"a": 2, "b": 1}

    points = [MetricPoint(time_stop_s=100.0, sig3=5), MetricPoint(time_stop_s=200.0, sig3=9)]
    cpath = write_metrics_csv(str(tmp_path / "m.csv"), points)
    lines = Path(cpath).read_text().strip().splitlines()
    assert lines[0].startswith("time_stop_s,proton_charge,num_peaks")
    assert lines[1].startswith("100.0,")
    assert len(lines) == 3


def test_build_provenance_shape() -> None:
    prov = build_provenance({"ipts": 1}, config_path="/SNS/TOPAZ/IPTS-1/shared/x.config")
    assert "crystalpilot_git_sha" in prov
    assert "mantid_version" in prov
    assert prov["args"] == {"ipts": 1}
    assert prov["reduction_config"].endswith("x.config")


def test_write_summary(tmp_path: Path) -> None:
    comparison = ComparisonResult(
        run_number=7,
        num_peaks_full=100,
        num_peaks_partial=80,
        strong_peak_recovery={"sig3": 0.9},
        beam_time_saved=0.4,
        headline="run 7: recovered 90% ...",
    )
    cutoff = CutoffResult(
        strategy="by_uncertainty",
        threshold=0.1,
        time_cut_s=300.0,
        total_time_s=500.0,
        crossed=True,
        time_fraction=0.6,
    )
    path = write_summary(str(tmp_path / "SUMMARY.md"), comparison, cutoff)
    text = Path(path).read_text()
    assert "run 7" in text
    assert "by_uncertainty" in text


def test_append_log(tmp_path: Path) -> None:
    log = str(tmp_path / "bench.log")
    append_log(log, "first")
    append_log(log, "second")
    lines = Path(log).read_text().strip().splitlines()
    assert len(lines) == 2
    assert "first" in lines[0]
