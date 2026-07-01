"""Fixtures + behavioural fakes for the CP-Bench harness tests.

The harness lives under ``scripts/cp_bench`` (a tool, not installed app
surface), so the repo root is put on ``sys.path`` here to make
``import scripts.cp_bench`` resolve. The fakes stand in for the three
side-effecting adapters (metadata reader, reduction engine, reducer) so the
pure/orchestration logic is exercised without Mantid or ``/SNS``.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional, Tuple, Type

import pytest

from scripts.cp_bench.models import MetricPoint, ReductionConfig, ReductionResult, RunInfo
from scripts.cp_bench.safety import safe_write_text


def isaw_peak_line(h: int, k: int, ell: int, inti: float, sigi: float) -> str:
    """Build one ISAW ``.integrate`` record-type-3 line (intI at col 14, sigI at 15)."""
    cols = ["3", "1", str(h), str(k), str(ell)] + ["0"] * 9 + [str(inti), str(sigi), "0", "1", "17"]
    return " ".join(cols)


def write_isaw_integrate(path: str, peaks: List[Tuple[int, int, int, float, float]]) -> str:
    """Write a minimal ISAW ``.integrate`` file with the given peaks."""
    header = "Version: 2.0  Facility: SNS  Instrument: TOPAZ\n"
    body = "\n".join(isaw_peak_line(*p) for p in peaks)
    return safe_write_text(path, header + body + "\n")


def write_isaw_mat(path: str, lattice: Tuple[float, float, float, float, float, float, float]) -> str:
    """Write a minimal ISAW ``.mat`` UB file whose 4th line carries the lattice."""
    ub = "0.1 0.0 0.0\n0.0 0.1 0.0\n0.0 0.0 0.1\n"
    lat = " ".join(f"{v:.4f}" for v in lattice) + "\n"
    sig = "0 0 0 0 0 0 0\n"
    return safe_write_text(path, ub + lat + sig)


class FakeMetadataReader:
    """Return canned :class:`RunInfo` per run (no Mantid)."""

    def __init__(self, runs: Dict[int, RunInfo]) -> None:
        self._runs = runs
        self.calls: List[int] = []

    def read_run_metadata(self, nxs_path: str, run_number: int) -> RunInfo:
        self.calls.append(run_number)
        return self._runs.get(run_number, RunInfo(run_number=run_number, nxs_path=nxs_path))


class FakeEngine:
    """Return a :class:`MetricPoint` per stop-time from an injected maker."""

    def __init__(self, maker: Callable[[float], MetricPoint]) -> None:
        self._maker = maker
        self.times: List[float] = []

    def metrics_at(self, nxs_path: str, time_stop_s: float, cfg: ReductionConfig, out_dir: str) -> MetricPoint:
        self.times.append(time_stop_s)
        return self._maker(time_stop_s)


class FakeReducer:
    """Write a tiny ``.integrate`` + ``.mat`` into the (writable) out dir."""

    def __init__(
        self,
        full_peaks: List[Tuple[int, int, int, float, float]],
        partial_peaks: List[Tuple[int, int, int, float, float]],
    ) -> None:
        self.full_peaks = full_peaks
        self.partial_peaks = partial_peaks
        self.calls: List[Tuple[str, Optional[float]]] = []

    def reduce(
        self,
        nxs_path: str,
        cfg: ReductionConfig,
        out_dir: str,
        time_stop_s: Optional[float],
        label: str,
    ) -> ReductionResult:
        self.calls.append((label, time_stop_s))
        peaks = self.full_peaks if label == "full" else self.partial_peaks
        integ = os.path.join(out_dir, f"{label}.integrate")
        mat = os.path.join(out_dir, f"{label}.mat")
        write_isaw_integrate(integ, peaks)
        write_isaw_mat(mat, (5.0, 5.0, 5.0, 90.0, 90.0, 90.0, 125.0))
        return ReductionResult(
            label=label,
            output_dir=out_dir,
            integrate_path=integ,
            ub_path=mat,
            num_peaks=len(peaks),
            lattice={"a": 5.0, "b": 5.0, "c": 5.0, "alpha": 90.0, "beta": 90.0, "gamma": 90.0, "volume": 125.0},
        )


@pytest.fixture
def fake_reader_factory() -> Type[FakeMetadataReader]:
    """Return the :class:`FakeMetadataReader` class (call with a run->RunInfo dict)."""
    return FakeMetadataReader


@pytest.fixture
def fake_engine_factory() -> Type[FakeEngine]:
    """Return the :class:`FakeEngine` class (call with a maker callable)."""
    return FakeEngine


@pytest.fixture
def fake_reducer_factory() -> Type[FakeReducer]:
    """Return the :class:`FakeReducer` class (call with full + partial peak lists)."""
    return FakeReducer


@pytest.fixture
def write_integrate() -> Callable[[str, List[Tuple[int, int, int, float, float]]], str]:
    """Return the ISAW ``.integrate`` writer helper."""
    return write_isaw_integrate


@pytest.fixture
def write_mat() -> Callable[[str, Tuple[float, float, float, float, float, float, float]], str]:
    """Return the ISAW ``.mat`` writer helper."""
    return write_isaw_mat
