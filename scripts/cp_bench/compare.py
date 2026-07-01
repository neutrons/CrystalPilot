"""Compare a partial-time reduction against the full-time reduction (pure).

Parses ISAW/SHELX ``.integrate`` peak files and computes agreement metrics
between the two reductions. The numeric comparison operates on lists of
:class:`Peak`, so it is fully unit-testable without any real reduction output;
:func:`parse_isaw_integrate` is the (best-effort, documented) file adapter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .models import ComparisonResult, CutoffResult, ReductionResult
from .safety import safe_open

#: Column indices of an ISAW peaks "record type 3" line (whitespace-split).
_H_COL, _K_COL, _L_COL, _INTI_COL, _SIGI_COL = 2, 3, 4, 14, 15

#: Sigma multiples reported for strong-peak recovery.
SIGMA_LEVELS: Tuple[int, ...] = (2, 3, 5, 10)


@dataclass(frozen=True)
class Peak:
    """One integrated reflection: Miller indices + integrated intensity/sigma."""

    h: int
    k: int
    ell: int  # Miller index l (spelled out to avoid the E741 ambiguous-name lint)
    inti: float
    sigi: float

    @property
    def key(self) -> Tuple[int, int, int]:
        return (self.h, self.k, self.ell)


@dataclass
class PeakAgreement:
    """Agreement metrics between a full and a partial peak list."""

    matched_hkls: int
    intensity_correlation: float
    intensity_scale: float
    strong_peak_recovery: Dict[str, float]


def parse_isaw_integrate(path: str) -> List[Peak]:
    """Parse an ISAW ``.integrate`` file into peaks (record-type-3 lines).

    Tolerant by design: lines that are not well-formed type-3 records are
    skipped so a stray header never aborts the comparison.
    """
    peaks: List[Peak] = []
    with safe_open(path, "r") as handle:
        for raw in handle:
            cols = str(raw).split()
            if len(cols) <= _SIGI_COL or cols[0] != "3":
                continue
            try:
                h = int(round(float(cols[_H_COL])))
                k = int(round(float(cols[_K_COL])))
                ell = int(round(float(cols[_L_COL])))
                inti = float(cols[_INTI_COL])
                sigi = float(cols[_SIGI_COL])
            except (ValueError, IndexError):
                continue
            if (h, k, ell) == (0, 0, 0):
                continue
            peaks.append(Peak(h, k, ell, inti, sigi))
    return peaks


def read_isaw_lattice(path: str) -> Dict[str, float]:
    """Read lattice constants from an ISAW ``.mat`` UB file (line 4: a b c α β γ V).

    Returns an empty dict if the file is missing or malformed, so a failed
    reduction never aborts the comparison.
    """
    try:
        with safe_open(path, "r") as handle:
            lines = [str(line) for line in handle]
    except OSError:
        return {}
    if len(lines) < 4:
        return {}
    cols = lines[3].split()
    if len(cols) < 6:
        return {}
    try:
        values = [float(c) for c in cols[:7]]
    except ValueError:
        return {}
    keys = ["a", "b", "c", "alpha", "beta", "gamma", "volume"]
    return {keys[i]: values[i] for i in range(min(len(keys), len(values)))}


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Pearson correlation of two equal-length sequences (0.0 if undefined)."""
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = math.sqrt(var_x * var_y)
    return cov / denom if denom > 0 else 0.0


def _least_squares_scale(full: Sequence[float], partial: Sequence[float]) -> float:
    """Best-fit scale s minimising ||partial - s*full|| (0.0 if undefined)."""
    denom = sum(f * f for f in full)
    if denom <= 0:
        return 0.0
    return sum(f * p for f, p in zip(full, partial, strict=False)) / denom


def strong_peak_counts(peaks: Sequence[Peak]) -> Dict[str, int]:
    """Count peaks with intensity above each sigma level."""
    counts: Dict[str, int] = {}
    for level in SIGMA_LEVELS:
        counts[f"sig{level}"] = sum(1 for p in peaks if p.sigi > 0 and p.inti > level * p.sigi)
    return counts


def compare_peaks(full: Sequence[Peak], partial: Sequence[Peak]) -> PeakAgreement:
    """Return agreement metrics between full and partial peak lists."""
    partial_by_key: Dict[Tuple[int, int, int], Peak] = {p.key: p for p in partial}
    matched_full: List[float] = []
    matched_partial: List[float] = []
    for peak in full:
        other = partial_by_key.get(peak.key)
        if other is not None:
            matched_full.append(peak.inti)
            matched_partial.append(other.inti)

    full_strong = strong_peak_counts(full)
    partial_strong = strong_peak_counts(partial)
    recovery: Dict[str, float] = {}
    for level in SIGMA_LEVELS:
        key = f"sig{level}"
        denom = full_strong[key]
        recovery[key] = (partial_strong[key] / denom) if denom > 0 else 0.0

    return PeakAgreement(
        matched_hkls=len(matched_full),
        intensity_correlation=_pearson(matched_full, matched_partial),
        intensity_scale=_least_squares_scale(matched_full, matched_partial),
        strong_peak_recovery=recovery,
    )


def lattice_delta(full: Dict[str, float], partial: Dict[str, float]) -> Dict[str, float]:
    """Per-key absolute difference of two lattice-constant dicts."""
    keys = set(full) | set(partial)
    return {k: abs(float(full.get(k, 0.0)) - float(partial.get(k, 0.0))) for k in sorted(keys)}


def build_comparison(
    run_number: int,
    full: ReductionResult,
    partial: ReductionResult,
    cutoff: CutoffResult,
) -> ComparisonResult:
    """Assemble the full partial-vs-full comparison + efficiency headline."""
    full_peaks = parse_isaw_integrate(full.integrate_path) if full.integrate_path else []
    partial_peaks = parse_isaw_integrate(partial.integrate_path) if partial.integrate_path else []
    agreement = compare_peaks(full_peaks, partial_peaks)

    recovery = agreement.strong_peak_recovery
    sig3_recovery = float(recovery.get("sig3", 0.0)) * 100.0
    beam_time_saved = max(0.0, 1.0 - cutoff.time_fraction)

    headline = (
        f"run {run_number}: stopping at {cutoff.time_fraction * 100:.0f}% of run time "
        f"recovered {sig3_recovery:.0f}% of I>3σ peaks "
        f"({len(partial_peaks)}/{len(full_peaks)} peaks); "
        f"beam time saved ≈ {beam_time_saved * 100:.0f}%."
    )

    return ComparisonResult(
        run_number=run_number,
        lattice_delta=lattice_delta(full.lattice, partial.lattice),
        num_peaks_full=len(full_peaks),
        num_peaks_partial=len(partial_peaks),
        matched_hkls=agreement.matched_hkls,
        intensity_correlation=agreement.intensity_correlation,
        intensity_scale=agreement.intensity_scale,
        strong_peak_recovery={k: float(v) for k, v in recovery.items()},
        time_fraction_used=cutoff.time_fraction,
        charge_fraction_used=cutoff.charge_fraction,
        beam_time_saved=beam_time_saved,
        headline=headline,
    )
