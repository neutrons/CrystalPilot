"""Phase 7 — orchestrate the whole benchmark for a run / IPTS.

Ties the phases together using injected adapters (metadata reader, reduction
engine, reducer) so the orchestration is unit-testable with fakes and has no
hard Mantid dependency. Per-run failures are captured and logged; the batch
never aborts on one bad run. All output lands under a writable root (never
``/SNS``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from . import compare, metrics, record
from .cutoff import choose_cutoff
from .discover import IptsManifest, MetadataReader, config_for_run, discover_ipts
from .metrics import ReductionEngine
from .reduce import Reducer, run_full_and_partial
from .safety import guard_output_root


@dataclass
class BenchOptions:
    """Tunable knobs for one benchmark run."""

    out_root: str
    n_steps: int = 12
    grid_kind: str = "log"
    cutoff_strategy: str = "by_uncertainty"
    cutoff_threshold: float = 0.1
    selector: str = "Max Peak"
    dry_run: bool = False
    instrument: str = "TOPAZ"


def ipts_dirs_from_app(ipts: int) -> Tuple[str, str]:
    """Resolve ``(nexus_dir, shared_dir)`` for an IPTS via the app path resolver.

    Imported lazily so the harness's pure paths never require the app at import
    time. Reads only — the returned dirs live under ``/SNS`` and are never
    written to.
    """
    from exphub.core.beamline import set_active
    from exphub.core.paths import resolver_for

    set_active("topaz")
    resolver = resolver_for(ipts)
    return os.path.join(resolver.ipts_dir, "nexus"), os.path.join(resolver.ipts_dir, "shared")


def process_run(
    run: Any,
    cfg: Any,
    ipts: int,
    engine: ReductionEngine,
    reducer: Reducer,
    options: BenchOptions,
    manifest: IptsManifest,
) -> Dict[str, Any]:
    """Run every phase for a single run and write its output tree."""
    timestamp = record.now_timestamp()
    paths = record.make_bench_paths(options.out_root, ipts, run.run_number, timestamp)
    log_path = os.path.join(paths.root, "bench.log")
    record.append_log(log_path, f"start run {run.run_number} (ipts {ipts})")

    record.write_json(os.path.join(paths.discovery, "manifest.json"), manifest.to_dict())
    record.write_json(os.path.join(paths.discovery, "run.json"), run.to_dict())
    record.write_json(os.path.join(paths.discovery, "config.json"), cfg.to_dict())

    grid = metrics.make_time_grid(run.duration_s, options.n_steps, options.grid_kind)
    record.append_log(log_path, f"metrics grid ({options.grid_kind}, {len(grid)} steps): {grid}")
    points = metrics.compute_metrics_vs_time(run, cfg, engine, grid, paths.metrics)
    record.write_metrics_csv(os.path.join(paths.metrics, f"{run.run_number}.csv"), points)

    cut = choose_cutoff(points, options.cutoff_strategy, options.cutoff_threshold, run.duration_s)
    record.write_json(os.path.join(paths.cutoff, f"{run.run_number}.json"), cut.to_dict())
    record.append_log(log_path, f"cutoff t={cut.time_cut_s:.1f}s crossed={cut.crossed}")

    full, partial = run_full_and_partial(run, cfg, reducer, cut, paths.reduction_full, paths.reduction_partial)
    record.write_json(os.path.join(paths.reduction_full, "result.json"), full.to_dict())
    record.write_json(os.path.join(paths.reduction_partial, "result.json"), partial.to_dict())

    comparison = compare.build_comparison(run.run_number, full, partial, cut)
    record.write_json(os.path.join(paths.comparison, "comparison.json"), comparison.to_dict())
    record.write_summary(os.path.join(paths.root, "SUMMARY.md"), comparison, cut)
    record.write_json(
        os.path.join(paths.root, "provenance.json"),
        record.build_provenance(vars(options), cfg.source_path),
    )
    record.append_log(log_path, f"done run {run.run_number}: {comparison.headline}")

    return {
        "run": run.run_number,
        "output_dir": paths.root,
        "cutoff": cut.to_dict(),
        "comparison": comparison.to_dict(),
        "full_error": full.error,
        "partial_error": partial.error,
    }


def run_ipts(
    ipts: int,
    nexus_dir: str,
    shared_dir: str,
    reader: MetadataReader,
    engine: Optional[ReductionEngine],
    reducer: Optional[Reducer],
    options: BenchOptions,
    runs_filter: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Discover an IPTS and benchmark each mapped run; return an aggregate summary.

    ``engine`` / ``reducer`` may be ``None`` only for a dry run (discovery only).
    """
    guard_output_root(options.out_root)
    manifest = discover_ipts(
        ipts, nexus_dir, shared_dir, reader, runs_filter=runs_filter, instrument=options.instrument
    )

    summary: Dict[str, Any] = {
        "ipts": ipts,
        "nexus_dir": nexus_dir,
        "shared_dir": shared_dir,
        "num_runs": len(manifest.runs),
        "num_configs": len(manifest.configs),
        "dry_run": options.dry_run,
        "results": [],
        "skipped": [],
    }

    if options.dry_run:
        summary["manifest"] = manifest.to_dict()
        return summary

    if engine is None or reducer is None:
        raise ValueError("engine and reducer are required unless options.dry_run is set")

    for run in manifest.runs:
        cfg = config_for_run(run.run_number, manifest.configs)
        if cfg is None:
            summary["skipped"].append({"run": run.run_number, "reason": "no reduction config mapped"})
            continue
        if run.error:
            summary["skipped"].append({"run": run.run_number, "reason": f"metadata error: {run.error}"})
            continue
        try:
            summary["results"].append(process_run(run, cfg, ipts, engine, reducer, options, manifest))
        except Exception as exc:
            summary["skipped"].append({"run": run.run_number, "reason": f"processing error: {exc}"})

    return summary
