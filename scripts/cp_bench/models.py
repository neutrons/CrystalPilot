"""Typed data contracts shared across CP-Bench phases.

Each phase reads/writes plain dataclasses that serialise to JSON, so phases can
run and be tested in isolation (a later phase consumes an earlier phase's JSON).
All fields are primitives or containers of primitives to keep serialisation
trivial and dependency-free.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _asdict(obj: Any) -> Dict[str, Any]:
    """Return a JSON-ready dict for a dataclass instance."""
    return dataclasses.asdict(obj)


@dataclass
class RunInfo:
    """Experiment info extracted from one NeXus event file."""

    run_number: int
    nxs_path: str
    title: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_s: float = 0.0
    total_proton_charge: float = 0.0
    sample_name: str = ""
    instrument: str = "TOPAZ"
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclass
class ReductionConfig:
    """A parsed ReduceSCD-style ``.config`` plus the file it came from."""

    source_path: str
    values: Dict[str, str] = field(default_factory=dict)
    run_numbers: List[int] = field(default_factory=list)

    # ---- typed accessors with sensible fallbacks -------------------------
    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)

    def get_float(self, key: str, default: float) -> float:
        raw = self.values.get(key)
        if raw is None or raw.lower() == "none":
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    def get_int(self, key: str, default: int) -> int:
        raw = self.values.get(key)
        if raw is None or raw.lower() == "none":
            return default
        try:
            return int(float(raw))
        except ValueError:
            return default

    def get_optional(self, key: str) -> Optional[str]:
        raw = self.values.get(key)
        if raw is None or raw.lower() == "none":
            return None
        return raw

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclass
class MetricPoint:
    """Quality metrics computed for the ``[0, time_stop_s]`` window of one run."""

    time_stop_s: float
    proton_charge: float = 0.0
    num_peaks: int = 0
    sig2: int = 0
    sig3: int = 0
    sig5: int = 0
    sig10: int = 0
    intensity_ratio: float = 0.0
    rsig: float = 0.0
    mean_i_over_sigma: float = 0.0
    num_unique_reflections: int = 0
    multiplicity: float = 0.0
    rmerge: float = 0.0
    rpim: float = 0.0
    lattice: Dict[str, float] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclass
class CutoffResult:
    """The chosen early-stop time and how it was derived."""

    strategy: str
    threshold: float
    time_cut_s: float
    total_time_s: float
    crossed: bool
    metric_at_cut: float = 0.0
    proton_charge_at_cut: float = 0.0
    time_fraction: float = 0.0
    charge_fraction: float = 0.0
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclass
class ReductionResult:
    """Where one reduction (full or partial) wrote its outputs + parsed summary."""

    label: str
    output_dir: str
    integrate_path: str = ""
    ub_path: str = ""
    returncode: int = 0
    lattice: Dict[str, float] = field(default_factory=dict)
    num_peaks: int = 0
    stats: Dict[str, float] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclass
class ComparisonResult:
    """Partial-vs-full deltas and the efficiency headline."""

    run_number: int
    lattice_delta: Dict[str, float] = field(default_factory=dict)
    num_peaks_full: int = 0
    num_peaks_partial: int = 0
    matched_hkls: int = 0
    intensity_correlation: float = 0.0
    intensity_scale: float = 0.0
    strong_peak_recovery: Dict[str, float] = field(default_factory=dict)
    time_fraction_used: float = 0.0
    charge_fraction_used: float = 0.0
    beam_time_saved: float = 0.0
    headline: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)
