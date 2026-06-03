"""Unit tests for the peak-selection strategies.

Each selector is a pure function of (peaks_ws, int_array, sig_array,
max_peak_idx, statistics). We stub the peaks workspace with a tiny in-memory
object that exposes ``getNumberPeaks`` and ``getPeak(i)`` returning fakes
with ``getIntMNP``, ``getIntHKL``, and ``getIntensity`` / ``getSigmaIntensity``.

That lets every selector branch be exercised without booting Mantid.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pytest

from exphub.techniques.single_crystal.models.temporal_analysis.selectors import (
    AllPeaksSelector,
    BraggPeaksSelector,
    DiffuseScatteringSelector,
    IndividualPeakSelector,
    MaxPeakSelector,
    PeakRatioSelector,
    SatellitePeaksSelector,
    SELECTOR_REGISTRY,
    SelectionResult,
    make_selector,
)


# ---------- test fixtures ----------

@dataclass
class FakePeak:
    h: int
    k: int
    l: int
    m: int = 0
    n: int = 0
    p: int = 0
    intensity: float = 100.0
    sigma: float = 10.0

    def getIntHKL(self):
        return (self.h, self.k, self.l)

    def getIntMNP(self):
        return (self.m, self.n, self.p)

    def getIntensity(self):
        return self.intensity

    def getSigmaIntensity(self):
        return self.sigma


class FakePeaksWS:
    def __init__(self, peaks: Sequence[FakePeak]):
        self._peaks = list(peaks)

    def getNumberPeaks(self):
        return len(self._peaks)

    def getPeak(self, i):
        return self._peaks[i]


def _arrays_for(ws: FakePeaksWS):
    n = ws.getNumberPeaks()
    ints = np.array([ws.getPeak(i).getIntensity() for i in range(n)])
    sigs = np.array([ws.getPeak(i).getSigmaIntensity() for i in range(n)])
    return ints, sigs


# ---------- AllPeaks (statistics-driven) ----------

def test_all_peaks_uses_statistics_row():
    ws = FakePeaksWS([FakePeak(1, 0, 0)])
    ints, sigs = _arrays_for(ws)
    sel = AllPeaksSelector()
    res = sel.select(ws, ints, sigs, max_peak_idx=0,
                     statistics={"Mean ((I)/sd(I))": 12.5})
    assert isinstance(res, SelectionResult)
    assert res.intensity_ratio == pytest.approx(12.5)
    assert res.rsig == pytest.approx(100 / 12.5)
    assert res.intensity_title is None  # uses figure defaults


# ---------- Bragg (filter MNP == 0) ----------

def test_bragg_includes_only_mnp_zero():
    ws = FakePeaksWS([
        FakePeak(1, 0, 0, intensity=100, sigma=10),    # Bragg
        FakePeak(1, 0, 0, m=1, intensity=50, sigma=10),  # satellite
        FakePeak(2, 0, 0, intensity=80, sigma=8),       # Bragg
    ])
    ints, sigs = _arrays_for(ws)
    res = BraggPeaksSelector().select(ws, ints, sigs, max_peak_idx=0, statistics={})
    assert res is not None
    # Mean of (100/10, 80/8) = mean(10, 10) = 10
    assert res.intensity_ratio == pytest.approx(10.0)
    assert res.aux["n_peaks"] == 2
    assert "Bragg" in res.intensity_yaxis


def test_bragg_returns_none_when_no_bragg_peaks():
    ws = FakePeaksWS([
        FakePeak(1, 0, 0, m=1, intensity=50, sigma=10),
    ])
    ints, sigs = _arrays_for(ws)
    res = BraggPeaksSelector().select(ws, ints, sigs, max_peak_idx=0, statistics={})
    assert res is None


def test_bragg_handles_peak_without_getIntMNP():
    """Mantid versions without modulation support → treat as all Bragg."""
    class LegacyPeak(FakePeak):
        def getIntMNP(self):
            raise AttributeError("legacy build")
    ws = FakePeaksWS([LegacyPeak(1, 0, 0, intensity=100, sigma=10)])
    ints, sigs = _arrays_for(ws)
    res = BraggPeaksSelector().select(ws, ints, sigs, max_peak_idx=0, statistics={})
    assert res is not None
    assert res.aux["n_peaks"] == 1


# ---------- Satellite (filter MNP != 0) ----------

def test_satellite_includes_only_nonzero_mnp():
    ws = FakePeaksWS([
        FakePeak(1, 0, 0, intensity=100, sigma=10),       # Bragg, skipped
        FakePeak(1, 0, 0, m=1, intensity=50, sigma=10),    # satellite
        FakePeak(1, 0, 0, n=1, intensity=40, sigma=5),     # satellite
    ])
    ints, sigs = _arrays_for(ws)
    res = SatellitePeaksSelector().select(ws, ints, sigs, max_peak_idx=0, statistics={})
    assert res is not None
    # Mean of (50/10, 40/5) = mean(5, 8) = 6.5
    assert res.intensity_ratio == pytest.approx(6.5)
    assert res.aux["n_peaks"] == 2


def test_satellite_empty_when_no_satellites():
    ws = FakePeaksWS([FakePeak(1, 0, 0, intensity=100, sigma=10)])
    ints, sigs = _arrays_for(ws)
    res = SatellitePeaksSelector().select(ws, ints, sigs, max_peak_idx=0, statistics={})
    assert res is None


# ---------- Max Peak ----------

def test_max_peak_uses_max_idx():
    ws = FakePeaksWS([
        FakePeak(1, 0, 0, intensity=50, sigma=10),
        FakePeak(2, 0, 0, intensity=200, sigma=10),  # brightest
        FakePeak(3, 0, 0, intensity=80, sigma=8),
    ])
    ints, sigs = _arrays_for(ws)
    res = MaxPeakSelector().select(ws, ints, sigs, max_peak_idx=1, statistics={})
    assert res is not None
    assert res.intensity_ratio == pytest.approx(200 / 10)


def test_max_peak_none_when_invalid_idx():
    ws = FakePeaksWS([FakePeak(1, 0, 0)])
    ints, sigs = _arrays_for(ws)
    res = MaxPeakSelector().select(ws, ints, sigs, max_peak_idx=-1, statistics={})
    assert res is None


# ---------- Diffuse Scattering (placeholder) ----------

def test_diffuse_always_none():
    res = DiffuseScatteringSelector().select(
        peaks_ws=None, int_array=np.array([]), sig_array=np.array([]),
        max_peak_idx=0, statistics={},
    )
    assert res is None


# ---------- Individual Peak ----------

def test_individual_peak_finds_match():
    ws = FakePeaksWS([
        FakePeak(0, 0, 0),
        FakePeak(1, 2, 3, intensity=200, sigma=20),
        FakePeak(4, 5, 6),
    ])
    ints, sigs = _arrays_for(ws)
    res = IndividualPeakSelector(hkl=(1, 2, 3)).select(
        ws, ints, sigs, max_peak_idx=0, statistics={}
    )
    assert res is not None
    assert res.intensity_ratio == pytest.approx(200 / 20)
    assert res.aux["matched_idx"] == 1
    assert res.aux["hkl"] == (1, 2, 3)


def test_individual_peak_no_match_returns_none():
    ws = FakePeaksWS([FakePeak(1, 0, 0)])
    ints, sigs = _arrays_for(ws)
    res = IndividualPeakSelector(hkl=(2, 0, 0)).select(
        ws, ints, sigs, max_peak_idx=0, statistics={}
    )
    assert res is None


def test_individual_peak_labels_carry_hkl():
    ws = FakePeaksWS([FakePeak(3, 1, 4, intensity=100, sigma=10)])
    ints, sigs = _arrays_for(ws)
    res = IndividualPeakSelector(hkl=(3, 1, 4)).select(
        ws, ints, sigs, max_peak_idx=0, statistics={}
    )
    assert res is not None
    assert "(3, 1, 4)" in res.intensity_title
    assert "(3, 1, 4)" in res.intensity_yaxis


# ---------- Peak Ratio ----------

def test_peak_ratio_basic():
    ws = FakePeaksWS([
        FakePeak(1, 0, 0, intensity=200, sigma=10),   # peak A
        FakePeak(0, 1, 0, intensity=50, sigma=5),     # peak B
    ])
    ints, sigs = _arrays_for(ws)
    res = PeakRatioSelector(hkl_a=(1, 0, 0), hkl_b=(0, 1, 0)).select(
        ws, ints, sigs, max_peak_idx=0, statistics={}
    )
    assert res is not None
    # ratio = 200 / 50 = 4.0
    assert res.intensity_ratio == pytest.approx(4.0)
    # σ(ratio)/ratio = sqrt((10/200)² + (5/50)²) = sqrt(0.0025 + 0.01) = sqrt(0.0125)
    expected_rel_unc = (0.0025 + 0.01) ** 0.5
    assert res.rsig == pytest.approx(expected_rel_unc * 100)


def test_peak_ratio_returns_none_if_either_missing():
    ws = FakePeaksWS([FakePeak(1, 0, 0, intensity=100, sigma=10)])
    ints, sigs = _arrays_for(ws)
    res = PeakRatioSelector(hkl_a=(1, 0, 0), hkl_b=(9, 9, 9)).select(
        ws, ints, sigs, max_peak_idx=0, statistics={}
    )
    assert res is None


def test_peak_ratio_label_overrides_present():
    ws = FakePeaksWS([
        FakePeak(1, 0, 0, intensity=100, sigma=10),
        FakePeak(0, 1, 0, intensity=50, sigma=5),
    ])
    ints, sigs = _arrays_for(ws)
    res = PeakRatioSelector(hkl_a=(1, 0, 0), hkl_b=(0, 1, 0)).select(
        ws, ints, sigs, max_peak_idx=0, statistics={}
    )
    assert res is not None
    # Peak Ratio mode overrides BOTH figures (top is the ratio, bottom is
    # propagated uncertainty — neither matches the legacy "Signal Noise
    # Ratio" / "σ(I)/I" labels).
    assert res.intensity_title is not None
    assert res.intensity_yaxis == "I_a / I_b"
    assert res.uncertainty_title is not None
    assert "ratio" in res.uncertainty_yaxis.lower()


# ---------- Registry / make_selector ----------

def test_registry_contains_all_modes():
    expected = {
        "All Peaks", "Bragg Peaks", "Satellite Peaks", "Max Peak",
        "Diffuse Scattering", "Individual Peak", "Peak Ratio",
    }
    assert expected <= set(SELECTOR_REGISTRY)


def test_make_selector_returns_none_for_unknown():
    assert make_selector("Not A Real Mode") is None


def test_make_selector_passes_kwargs_to_factory():
    sel = make_selector("Individual Peak", hkl=(2, 3, 4))
    assert isinstance(sel, IndividualPeakSelector)
    assert sel.hkl == (2, 3, 4)


def test_make_selector_ignores_unused_kwargs():
    # AllPeaks accepts and ignores hkl=/hkl_a=/hkl_b= — same kwargs the
    # workflow blasts at every selector each cycle.
    sel = make_selector("All Peaks", hkl=(1, 2, 3), hkl_a=(0, 0, 0), hkl_b=(1, 1, 1))
    assert isinstance(sel, AllPeaksSelector)
