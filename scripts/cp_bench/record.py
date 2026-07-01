"""Phase 6 — output layout, provenance, and result serialisation.

All writes go through :mod:`.safety`, so nothing here can touch ``/SNS``. The
per-run layout is::

    <out_root>/IPTS-<n>/CP-bench/<run>/<timestamp>/
        discovery/manifest.json
        metrics_vs_time/<run>.csv
        cutoff/<run>.json
        reduction_full/    reduction_partial/
        comparison/comparison.json
        provenance.json  bench.log  SUMMARY.md
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence

from .models import ComparisonResult, CutoffResult, MetricPoint
from .safety import safe_makedirs, safe_write_text

_METRIC_COLUMNS: tuple[str, ...] = (
    "time_stop_s",
    "proton_charge",
    "num_peaks",
    "sig2",
    "sig3",
    "sig5",
    "sig10",
    "intensity_ratio",
    "rsig",
    "mean_i_over_sigma",
    "num_unique_reflections",
    "multiplicity",
    "rmerge",
    "rpim",
    "error",
)


@dataclass
class BenchPaths:
    """Resolved output directories for one benchmarked run."""

    root: str
    discovery: str
    metrics: str
    cutoff: str
    reduction_full: str
    reduction_partial: str
    comparison: str


def default_out_root() -> str:
    """Default output root: the user's home directory."""
    return os.path.expanduser("~")


def now_timestamp() -> str:
    """UTC timestamp suitable for a directory name (``YYYYmmdd-HHMMSS``)."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def make_bench_paths(out_root: str, ipts: int, run: int, timestamp: str) -> BenchPaths:
    """Create (writable-guarded) the per-run output tree and return its paths."""
    root = os.path.join(out_root, f"IPTS-{ipts}", "CP-bench", str(run), timestamp)
    paths = BenchPaths(
        root=root,
        discovery=os.path.join(root, "discovery"),
        metrics=os.path.join(root, "metrics_vs_time"),
        cutoff=os.path.join(root, "cutoff"),
        reduction_full=os.path.join(root, "reduction_full"),
        reduction_partial=os.path.join(root, "reduction_partial"),
        comparison=os.path.join(root, "comparison"),
    )
    for directory in vars(paths).values():
        safe_makedirs(directory)
    return paths


def write_json(path: str, obj: Any) -> str:
    """Serialise ``obj`` as pretty JSON through the read-only guard."""
    return safe_write_text(path, json.dumps(obj, indent=2, sort_keys=True))


def write_metrics_csv(path: str, points: Sequence[MetricPoint]) -> str:
    """Write the metrics-vs-time series as CSV (one row per time slice)."""
    lines: List[str] = [",".join(_METRIC_COLUMNS)]
    for point in points:
        row = point.to_dict()
        lines.append(",".join(_csv_cell(row.get(col, "")) for col in _METRIC_COLUMNS))
    return safe_write_text(path, "\n".join(lines) + "\n")


def _csv_cell(value: Any) -> str:
    """Render a CSV cell, quoting anything containing a comma or quote."""
    text = "" if value is None else str(value)
    if "," in text or '"' in text or "\n" in text:
        return '"' + text.replace('"', '""') + '"'
    return text


def _git_sha(repo_root: str) -> str:
    """Best-effort short git SHA of the CrystalPilot checkout (``unknown`` on failure)."""
    try:
        out = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _mantid_version() -> str:
    """Best-effort Mantid version string (``unavailable`` if not importable)."""
    try:
        import mantid

        return str(getattr(mantid, "__version__", "unknown"))
    except Exception:
        return "unavailable"


def build_provenance(args: Dict[str, Any], config_path: str = "") -> Dict[str, Any]:
    """Assemble a provenance record (git SHA, Mantid version, args, host, time)."""
    repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return {
        "timestamp_utc": now_timestamp(),
        "crystalpilot_git_sha": _git_sha(repo_root),
        "mantid_version": _mantid_version(),
        "hostname": os.uname().nodename if hasattr(os, "uname") else "unknown",
        "reduction_config": config_path,
        "args": args,
        "cp_bench_version": _cp_bench_version(),
    }


def _cp_bench_version() -> str:
    """Return the CP-Bench package version (``unknown`` if not importable)."""
    try:
        from . import __version__

        return __version__
    except Exception:
        return "unknown"


def write_summary(path: str, comparison: ComparisonResult, cutoff: CutoffResult) -> str:
    """Write a short human-readable SUMMARY.md for one run."""
    lattice = "  ".join(f"Δ{k}={v:.4g}" for k, v in comparison.lattice_delta.items())
    recovery = "  ".join(f"{k}={v * 100:.0f}%" for k, v in comparison.strong_peak_recovery.items())
    text = (
        f"# CP-Bench — run {comparison.run_number}\n\n"
        f"{comparison.headline}\n\n"
        f"## Cutoff\n"
        f"- strategy: `{cutoff.strategy}` (threshold {cutoff.threshold})\n"
        f"- t_cut: {cutoff.time_cut_s:.1f} s of {cutoff.total_time_s:.1f} s "
        f"({cutoff.time_fraction * 100:.1f}% of run; {cutoff.charge_fraction * 100:.1f}% of charge)\n"
        f"- rule triggered: {cutoff.crossed}{(' — ' + cutoff.note) if cutoff.note else ''}\n\n"
        f"## Partial vs full reduction\n"
        f"- peaks: {comparison.num_peaks_partial} (partial) / {comparison.num_peaks_full} (full)\n"
        f"- matched HKLs: {comparison.matched_hkls}\n"
        f"- intensity correlation: {comparison.intensity_correlation:.4f} "
        f"(scale {comparison.intensity_scale:.4f})\n"
        f"- strong-peak recovery: {recovery}\n"
        f"- lattice deltas: {lattice or 'n/a'}\n"
        f"- beam time saved: {comparison.beam_time_saved * 100:.1f}%\n"
    )
    return safe_write_text(path, text)


def append_log(path: str, message: str) -> None:
    """Append a timestamped line to the run log (guarded write)."""
    from .safety import assert_writable

    assert_writable(path)
    safe_makedirs(os.path.dirname(path) or ".")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")
