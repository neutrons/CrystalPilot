"""Cutoff-rule functions: pick an early-stop time from a metrics-vs-time series.

Pure functions over a list of :class:`~cp_bench.models.MetricPoint` (no Mantid,
no I/O). The default strategy mirrors the app's live auto-stop
(``eic_auto_stop_strategy == "By Uncertainty"`` /
``eic_auto_stop_uncertainty_threshold`` — see
``techniques/single_crystal/view_models/steering.py``), so the benchmark
measures the app's *actual* stopping behaviour rather than a re-invention.
"""

from __future__ import annotations

from typing import Callable, List, Sequence, Tuple

from .models import CutoffResult, MetricPoint

#: Selectable cutoff strategies (CLI ``--cutoff-strategy``).
STRATEGIES: Tuple[str, ...] = (
    "by_uncertainty",
    "by_snr",
    "rmerge_below",
    "sig3_plateau",
    "fraction_of_full",
)


def _first_crossing(
    points: Sequence[MetricPoint],
    value_of: Callable[[MetricPoint], float],
    passes: Callable[[float], bool],
) -> int:
    """Return the index of the first point whose value passes, else ``-1``."""
    for idx, point in enumerate(points):
        if point.error:
            continue
        if passes(value_of(point)):
            return idx
    return -1


def _plateau_index(
    points: Sequence[MetricPoint],
    value_of: Callable[[MetricPoint], float],
    rel_epsilon: float,
) -> int:
    """Return the first index where the value's step-to-step relative change < epsilon."""
    prev: float | None = None
    for idx, point in enumerate(points):
        if point.error:
            continue
        cur = value_of(point)
        if prev is not None:
            denom = abs(prev) if abs(prev) > 1e-12 else 1.0
            if abs(cur - prev) / denom < rel_epsilon:
                return idx
        prev = cur
    return -1


def choose_cutoff(
    points: Sequence[MetricPoint],
    strategy: str = "by_uncertainty",
    threshold: float = 0.1,
    total_time_s: float | None = None,
) -> CutoffResult:
    """Select an early-stop time from a metrics series for the given strategy.

    If the rule never triggers, the cutoff is the full run duration with
    ``crossed=False`` (i.e. "no early stop was warranted").
    """
    usable: List[MetricPoint] = [p for p in points if not p.error]
    total = total_time_s if total_time_s is not None else (usable[-1].time_stop_s if usable else 0.0)
    total_charge = max((p.proton_charge for p in usable), default=0.0)

    if not usable:
        return CutoffResult(
            strategy=strategy,
            threshold=threshold,
            time_cut_s=total,
            total_time_s=total,
            crossed=False,
            note="no usable metric points",
        )

    idx = -1
    metric_value = 0.0
    if strategy == "by_uncertainty":
        idx = _first_crossing(usable, lambda p: p.rsig, lambda v: v < threshold)
    elif strategy == "by_snr":
        idx = _first_crossing(usable, lambda p: p.mean_i_over_sigma, lambda v: v >= threshold)
    elif strategy == "rmerge_below":
        idx = _first_crossing(usable, lambda p: p.rmerge, lambda v: 0.0 < v < threshold)
    elif strategy == "sig3_plateau":
        idx = _plateau_index(usable, lambda p: float(p.sig3), threshold)
    elif strategy == "fraction_of_full":
        target = threshold * total
        idx = _first_crossing(usable, lambda p: p.time_stop_s, lambda v: v >= target)
    else:
        raise ValueError(f"unknown cutoff strategy {strategy!r}; choose from {STRATEGIES}")

    crossed = idx >= 0
    chosen = usable[idx] if crossed else usable[-1]
    if crossed:
        metric_value = {
            "by_uncertainty": chosen.rsig,
            "by_snr": chosen.mean_i_over_sigma,
            "rmerge_below": chosen.rmerge,
            "sig3_plateau": float(chosen.sig3),
            "fraction_of_full": chosen.time_stop_s,
        }[strategy]

    time_cut = chosen.time_stop_s
    return CutoffResult(
        strategy=strategy,
        threshold=threshold,
        time_cut_s=time_cut,
        total_time_s=total,
        crossed=crossed,
        metric_at_cut=metric_value,
        proton_charge_at_cut=chosen.proton_charge,
        time_fraction=(time_cut / total) if total > 0 else 0.0,
        charge_fraction=(chosen.proton_charge / total_charge) if total_charge > 0 else 0.0,
        note="" if crossed else "rule never triggered — using full run duration",
    )
