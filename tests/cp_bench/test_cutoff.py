"""Tests for the cutoff-rule functions."""

from __future__ import annotations

from typing import List

import pytest

from scripts.cp_bench.cutoff import choose_cutoff
from scripts.cp_bench.models import MetricPoint


def _series() -> List[MetricPoint]:
    # time, rsig (falling), snr (rising), rmerge (falling), sig3 (rising→plateau)
    rows = [
        (100.0, 0.40, 2.0, 0.50, 10),
        (200.0, 0.20, 6.0, 0.30, 40),
        (300.0, 0.08, 12.0, 0.12, 95),
        (400.0, 0.05, 15.0, 0.08, 98),
        (500.0, 0.04, 16.0, 0.06, 99),
    ]
    points = []
    for i, (t, rsig, snr, rmerge, sig3) in enumerate(rows):
        points.append(
            MetricPoint(
                time_stop_s=t,
                proton_charge=float(i + 1),
                rsig=rsig,
                mean_i_over_sigma=snr,
                rmerge=rmerge,
                sig3=sig3,
            )
        )
    return points


def test_by_uncertainty_first_below_threshold() -> None:
    cut = choose_cutoff(_series(), strategy="by_uncertainty", threshold=0.1, total_time_s=500.0)
    assert cut.crossed
    assert cut.time_cut_s == 300.0
    assert cut.time_fraction == pytest.approx(0.6)


def test_by_snr_first_above_threshold() -> None:
    cut = choose_cutoff(_series(), strategy="by_snr", threshold=10.0, total_time_s=500.0)
    assert cut.crossed
    assert cut.time_cut_s == 300.0


def test_rmerge_below() -> None:
    cut = choose_cutoff(_series(), strategy="rmerge_below", threshold=0.1, total_time_s=500.0)
    assert cut.crossed
    assert cut.time_cut_s == 400.0


def test_fraction_of_full() -> None:
    cut = choose_cutoff(_series(), strategy="fraction_of_full", threshold=0.5, total_time_s=500.0)
    assert cut.crossed
    assert cut.time_cut_s == 300.0  # first time >= 250s


def test_no_crossing_uses_full_duration() -> None:
    cut = choose_cutoff(_series(), strategy="by_uncertainty", threshold=0.001, total_time_s=500.0)
    assert not cut.crossed
    assert cut.time_cut_s == 500.0
    assert "never" in cut.note


def test_empty_series() -> None:
    cut = choose_cutoff([], strategy="by_uncertainty", threshold=0.1)
    assert not cut.crossed
    assert cut.time_cut_s == 0.0


def test_unknown_strategy_raises() -> None:
    with pytest.raises(ValueError, match="unknown cutoff strategy"):
        choose_cutoff(_series(), strategy="bogus", threshold=1.0)
