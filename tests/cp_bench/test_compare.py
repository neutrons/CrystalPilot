"""Tests for the partial-vs-full comparison logic."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Tuple

import pytest

from scripts.cp_bench.compare import (
    Peak,
    build_comparison,
    compare_peaks,
    lattice_delta,
    parse_isaw_integrate,
    read_isaw_lattice,
    strong_peak_counts,
)
from scripts.cp_bench.models import CutoffResult, ReductionResult

IntegrateWriter = Callable[[str, List[Tuple[int, int, int, float, float]]], str]
MatWriter = Callable[[str, Tuple[float, float, float, float, float, float, float]], str]


def test_parse_isaw_integrate_roundtrip(tmp_path: Path, write_integrate: IntegrateWriter) -> None:
    path = str(tmp_path / "x.integrate")
    write_integrate(path, [(1, 0, 0, 100.0, 5.0), (0, 2, 0, 40.0, 8.0)])
    peaks = parse_isaw_integrate(path)
    assert [p.key for p in peaks] == [(1, 0, 0), (0, 2, 0)]
    assert peaks[0].inti == 100.0
    assert peaks[1].sigi == 8.0


def test_strong_peak_counts() -> None:
    peaks = [Peak(1, 0, 0, 100.0, 5.0), Peak(0, 1, 0, 12.0, 5.0), Peak(0, 0, 1, 4.0, 5.0)]
    counts = strong_peak_counts(peaks)
    assert counts["sig2"] == 2  # 100>10, 12>10
    assert counts["sig3"] == 1  # only 100>15
    assert counts["sig10"] == 1


def test_compare_peaks_perfect_match() -> None:
    full = [Peak(1, 0, 0, 100.0, 5.0), Peak(0, 1, 0, 50.0, 5.0)]
    partial = [Peak(1, 0, 0, 50.0, 5.0), Peak(0, 1, 0, 25.0, 5.0)]  # exactly half
    agree = compare_peaks(full, partial)
    assert agree.matched_hkls == 2
    assert agree.intensity_correlation == pytest.approx(1.0)
    assert agree.intensity_scale == pytest.approx(0.5)


def test_compare_peaks_partial_missing() -> None:
    full = [Peak(1, 0, 0, 100.0, 5.0), Peak(0, 1, 0, 50.0, 5.0)]
    partial = [Peak(1, 0, 0, 90.0, 5.0)]  # missing (0,1,0)
    agree = compare_peaks(full, partial)
    assert agree.matched_hkls == 1


def test_read_isaw_lattice(tmp_path: Path, write_mat: MatWriter) -> None:
    path = str(tmp_path / "x.mat")
    write_mat(path, (5.1, 5.2, 5.3, 90.0, 91.0, 92.0, 140.0))
    lat = read_isaw_lattice(path)
    assert lat["a"] == 5.1
    assert lat["gamma"] == 92.0
    assert lat["volume"] == 140.0


def test_lattice_delta() -> None:
    delta = lattice_delta({"a": 5.0, "b": 5.0}, {"a": 5.2, "b": 5.0})
    assert delta["a"] == pytest.approx(0.2)
    assert delta["b"] == pytest.approx(0.0)


def test_build_comparison_headline(tmp_path: Path, write_integrate: IntegrateWriter) -> None:
    full_path = str(tmp_path / "full.integrate")
    partial_path = str(tmp_path / "partial.integrate")
    write_integrate(full_path, [(1, 0, 0, 100.0, 5.0), (0, 1, 0, 60.0, 5.0), (0, 0, 1, 30.0, 5.0)])
    write_integrate(partial_path, [(1, 0, 0, 90.0, 5.0), (0, 1, 0, 55.0, 5.0)])

    full = ReductionResult(label="full", output_dir="", integrate_path=full_path, lattice={"a": 5.0})
    partial = ReductionResult(label="partial", output_dir="", integrate_path=partial_path, lattice={"a": 5.05})
    cut = CutoffResult(
        strategy="by_uncertainty",
        threshold=0.1,
        time_cut_s=300.0,
        total_time_s=500.0,
        crossed=True,
        time_fraction=0.6,
    )

    result = build_comparison(42, full, partial, cut)
    assert result.run_number == 42
    assert result.num_peaks_full == 3
    assert result.num_peaks_partial == 2
    assert result.matched_hkls == 2
    assert result.lattice_delta["a"] == pytest.approx(0.05)
    assert result.beam_time_saved == pytest.approx(0.4)
    assert "run 42" in result.headline
