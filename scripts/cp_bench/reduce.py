"""Phase 4 — run the official reduction on the full and the partial window.

Both reductions use the *same* discovered config; the only variable is the time
window (full run vs ``[0, t_cut]``). The reduction mechanism (pre-slice +
``ReduceSCD`` invocation) lives behind an injected :class:`Reducer`; this module
only orchestrates and enforces that every output directory is writable (never
under ``/SNS``).
"""

from __future__ import annotations

from typing import Optional, Protocol, Tuple

from .models import CutoffResult, ReductionConfig, ReductionResult, RunInfo
from .safety import safe_makedirs


class Reducer(Protocol):
    """Reduce a run (optionally time-limited) with a given config, into ``out_dir``."""

    def reduce(
        self,
        nxs_path: str,
        cfg: ReductionConfig,
        out_dir: str,
        time_stop_s: Optional[float],
        label: str,
    ) -> ReductionResult:
        """Reduce full (``time_stop_s is None``) or partial (``[0, time_stop_s]``)."""
        ...


def run_full_and_partial(
    run: RunInfo,
    cfg: ReductionConfig,
    reducer: Reducer,
    cutoff: CutoffResult,
    full_dir: str,
    partial_dir: str,
) -> Tuple[ReductionResult, ReductionResult]:
    """Reduce the full run and the pre-cutoff window; return both results.

    Output directories are created through the read-only guard, so a
    misconfigured path that resolves under ``/SNS`` fails before any reduction
    runs. A failure in one reduction is captured on its result, not raised, so
    the batch can continue.
    """
    safe_makedirs(full_dir)
    safe_makedirs(partial_dir)

    try:
        full = reducer.reduce(run.nxs_path, cfg, full_dir, None, "full")
    except Exception as exc:
        full = ReductionResult(label="full", output_dir=full_dir, error=str(exc))

    try:
        partial = reducer.reduce(run.nxs_path, cfg, partial_dir, cutoff.time_cut_s, "partial")
    except Exception as exc:
        partial = ReductionResult(label="partial", output_dir=partial_dir, error=str(exc))

    return full, partial
