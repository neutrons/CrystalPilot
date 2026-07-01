"""CP-Bench CLI — ``python -m scripts.cp_bench --ipts N [...]``.

Wires the real adapters (Mantid metadata reader, pipeline metrics engine,
ReduceSCD reducer) into the batch orchestrator. ``--dry-run`` performs discovery
only and needs neither the engine nor the reducer. Output goes under
``<out>/IPTS-<n>/CP-bench/`` and never under ``/SNS``.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .batch import BenchOptions, ipts_dirs_from_app, run_ipts
from .cutoff import STRATEGIES
from .discover import MetadataReader
from .metrics import ReductionEngine
from .record import default_out_root
from .reduce import Reducer
from .reduce_config import expand_run_numbers
from .safety import ReadOnlyPathError, guard_output_root


def build_parser() -> argparse.ArgumentParser:
    """Construct the CP-Bench argument parser."""
    parser = argparse.ArgumentParser(
        prog="cp_bench",
        description="Early-stopping reduction benchmark for TOPAZ (reads /SNS, never writes it).",
    )
    parser.add_argument("--ipts", type=int, nargs="+", required=True, help="IPTS number(s) to benchmark.")
    parser.add_argument("--runs", type=str, default="", help="Run filter, e.g. '12,15,20:23' (default: all).")
    parser.add_argument("--out", type=str, default=default_out_root(), help="Output root (default: ~).")
    parser.add_argument("--n-steps", type=int, default=12, help="Number of time slices (default: 12).")
    parser.add_argument("--grid", choices=["log", "linear"], default="log", help="Time-grid spacing.")
    parser.add_argument("--cutoff-strategy", choices=list(STRATEGIES), default="by_uncertainty")
    parser.add_argument("--cutoff-threshold", type=float, default=0.1)
    parser.add_argument("--selector", type=str, default="Max Peak", help="Live-pipeline peak selector mode.")
    parser.add_argument("--point-group", type=str, default="-1", help="Point group for merge statistics.")
    parser.add_argument("--reducer", type=str, default="", help="ReduceSCD_Parallel.py path (needed unless --dry-run).")
    parser.add_argument("--instrument", type=str, default="TOPAZ")
    parser.add_argument("--dry-run", action="store_true", help="Discovery only; write and reduce nothing.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Run the benchmark for the requested IPTS list; return a process exit code."""
    args = build_parser().parse_args(argv)

    try:
        guard_output_root(args.out)
    except ReadOnlyPathError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not args.dry_run and not args.reducer:
        print("error: --reducer is required unless --dry-run is set", file=sys.stderr)
        return 2

    runs_filter = expand_run_numbers(args.runs) or None
    options = BenchOptions(
        out_root=args.out,
        n_steps=args.n_steps,
        grid_kind=args.grid,
        cutoff_strategy=args.cutoff_strategy,
        cutoff_threshold=args.cutoff_threshold,
        selector=args.selector,
        dry_run=args.dry_run,
        instrument=args.instrument,
    )

    reader = _make_reader(args.instrument)
    engine: Optional[ReductionEngine] = None
    reducer: Optional[Reducer] = None
    if not args.dry_run:
        engine = _make_engine(args.selector, args.point_group)
        reducer = _make_reducer(args.reducer, args.instrument)

    summaries = []
    for ipts in args.ipts:
        nexus_dir, shared_dir = ipts_dirs_from_app(ipts)
        summary = run_ipts(ipts, nexus_dir, shared_dir, reader, engine, reducer, options, runs_filter=runs_filter)
        summaries.append(summary)

    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 0


def _make_reader(instrument: str) -> MetadataReader:
    from .adapters.mantid_metadata import MantidMetadataReader

    return MantidMetadataReader(instrument=instrument)


def _make_engine(selector: str, point_group: str) -> ReductionEngine:
    from .adapters.pipeline_engine import PipelineReductionEngine

    return PipelineReductionEngine(selector=selector, point_group=point_group)


def _make_reducer(reducer_script: str, instrument: str) -> Reducer:
    from .adapters.reducescd import ReduceSCDReducer

    return ReduceSCDReducer(reducer_script=reducer_script, instrument=instrument)


if __name__ == "__main__":
    raise SystemExit(main())
