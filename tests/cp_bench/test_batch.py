"""End-to-end orchestration tests for run_ipts (all side effects faked)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import pytest

from scripts.cp_bench.batch import BenchOptions, run_ipts
from scripts.cp_bench.discover import MetadataReader
from scripts.cp_bench.metrics import ReductionEngine
from scripts.cp_bench.models import MetricPoint, RunInfo
from scripts.cp_bench.reduce import Reducer
from scripts.cp_bench.safety import ReadOnlyPathError

Peaks = List[Tuple[int, int, int, float, float]]
ReaderFactory = Callable[[Dict[int, RunInfo]], MetadataReader]
EngineFactory = Callable[[Callable[[float], MetricPoint]], ReductionEngine]
ReducerFactory = Callable[[Peaks, Peaks], Reducer]

_RSIG = {100.0: 0.40, 200.0: 0.20, 300.0: 0.08, 400.0: 0.05, 500.0: 0.04}


def _tree(tmp_path: Path) -> tuple[str, str]:
    nexus = tmp_path / "nexus"
    nexus.mkdir()
    (nexus / "TOPAZ_100.nxs.h5").write_text("")
    shared = tmp_path / "shared" / "ReductionGUI"
    shared.mkdir(parents=True)
    (shared / "reduce.config").write_text(
        "instrument_name TOPAZ\nrun_nums 100\ncell_type Monoclinic\ncentering P\nmin_d 3\nmax_d 25\n"
    )
    return str(nexus), str(tmp_path / "shared")


def _maker(t: float) -> MetricPoint:
    return MetricPoint(time_stop_s=t, proton_charge=t / 100.0, rsig=_RSIG.get(t, 1.0), sig3=int(t))


def _options(out_root: str, dry_run: bool = False) -> BenchOptions:
    return BenchOptions(
        out_root=out_root,
        n_steps=5,
        grid_kind="linear",
        cutoff_strategy="by_uncertainty",
        cutoff_threshold=0.1,
        dry_run=dry_run,
    )


def test_run_ipts_end_to_end(
    tmp_path: Path,
    fake_reader_factory: ReaderFactory,
    fake_engine_factory: EngineFactory,
    fake_reducer_factory: ReducerFactory,
) -> None:
    nexus_dir, shared_dir = _tree(tmp_path)
    out_root = str(tmp_path / "out")
    reader = fake_reader_factory({100: RunInfo(run_number=100, nxs_path="", duration_s=500.0, total_proton_charge=5.0)})
    engine = fake_engine_factory(_maker)
    reducer = fake_reducer_factory(
        [(1, 0, 0, 100.0, 5.0), (0, 1, 0, 60.0, 5.0)],  # full
        [(1, 0, 0, 90.0, 5.0)],  # partial
    )

    summary = run_ipts(100, nexus_dir, shared_dir, reader, engine, reducer, _options(out_root))

    assert len(summary["results"]) == 1
    result = summary["results"][0]
    assert result["run"] == 100
    # Cutoff fired at 300s (first rsig < 0.1) and drove the partial reduction.
    assert result["cutoff"]["time_cut_s"] == 300.0

    run_dir = result["output_dir"]
    for rel in ("SUMMARY.md", "provenance.json"):
        assert os.path.isfile(os.path.join(run_dir, rel))
    assert os.path.isfile(os.path.join(run_dir, "comparison", "comparison.json"))
    assert os.path.isfile(os.path.join(run_dir, "metrics_vs_time", "100.csv"))
    assert os.path.isfile(os.path.join(run_dir, "reduction_full", "result.json"))
    assert os.path.isfile(os.path.join(run_dir, "reduction_partial", "result.json"))
    assert result["comparison"]["num_peaks_full"] == 2
    assert result["comparison"]["num_peaks_partial"] == 1


def test_dry_run_writes_nothing(
    tmp_path: Path,
    fake_reader_factory: ReaderFactory,
) -> None:
    nexus_dir, shared_dir = _tree(tmp_path)
    out_root = str(tmp_path / "out")
    reader = fake_reader_factory({100: RunInfo(run_number=100, nxs_path="", duration_s=500.0)})

    summary = run_ipts(100, nexus_dir, shared_dir, reader, None, None, _options(out_root, dry_run=True))

    assert summary["dry_run"] is True
    assert "manifest" in summary
    assert summary["results"] == []
    # No output tree was created.
    assert not os.path.exists(out_root)


def test_out_root_under_sns_is_refused(
    fake_reader_factory: ReaderFactory,
) -> None:
    reader = fake_reader_factory({})
    with pytest.raises(ReadOnlyPathError):
        run_ipts(
            100,
            "/SNS/TOPAZ/IPTS-100/nexus",
            "/SNS/TOPAZ/IPTS-100/shared",
            reader,
            None,
            None,
            _options("/SNS/TOPAZ/IPTS-100/CP-bench", dry_run=True),
        )
