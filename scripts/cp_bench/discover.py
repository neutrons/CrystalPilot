"""Phase 1 — discover NeXus files, experiment info, and reduction configs.

Everything here is read-only with respect to ``/SNS``. The filesystem/glob and
config-matching logic is pure and testable; per-file metadata extraction is
delegated to an injected :class:`MetadataReader` (the real one lives in
:mod:`.adapters.mantid_metadata`; tests pass a fake).
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol

from .models import ReductionConfig, RunInfo
from .reduce_config import parse_config_file

_RUN_RE = re.compile(r"_(\d+)\.nxs(?:\.h5)?$", re.IGNORECASE)


class MetadataReader(Protocol):
    """Reads experiment metadata from a NeXus event file (no writes)."""

    def read_run_metadata(self, nxs_path: str, run_number: int) -> RunInfo:
        """Return a :class:`RunInfo` for the given file/run."""
        ...


@dataclass
class IptsManifest:
    """The discovery result for one IPTS: runs, configs, and their mapping."""

    ipts: int
    nexus_dir: str
    shared_dir: str
    runs: List[RunInfo] = field(default_factory=list)
    configs: List[ReductionConfig] = field(default_factory=list)
    run_config_map: Dict[int, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "ipts": self.ipts,
            "nexus_dir": self.nexus_dir,
            "shared_dir": self.shared_dir,
            "runs": [r.to_dict() for r in self.runs],
            "configs": [c.to_dict() for c in self.configs],
            "run_config_map": {str(k): v for k, v in self.run_config_map.items()},
        }


def find_nexus_files(nexus_dir: str, instrument: str = "TOPAZ") -> Dict[int, str]:
    """Map run number -> NeXus path for ``<nexus_dir>/<instrument>_*.nxs[.h5]``."""
    found: Dict[int, str] = {}
    patterns = [
        os.path.join(nexus_dir, f"{instrument}_*.nxs.h5"),
        os.path.join(nexus_dir, f"{instrument}_*.nxs"),
    ]
    for pattern in patterns:
        for path in glob.glob(pattern):
            match = _RUN_RE.search(os.path.basename(path))
            if not match:
                continue
            run = int(match.group(1))
            # Prefer .nxs.h5 over legacy .nxs if both exist for a run.
            if run not in found or path.endswith(".h5"):
                found[run] = path
    return found


def find_reduction_configs(shared_dir: str) -> List[ReductionConfig]:
    """Find and parse ``*.config`` files under ``shared_dir`` (ReductionGUI first)."""
    paths = sorted(
        glob.glob(os.path.join(shared_dir, "**", "*.config"), recursive=True),
        key=lambda p: (0 if "reductiongui" in p.lower() else 1, p.lower()),
    )
    configs: List[ReductionConfig] = []
    for path in paths:
        try:
            configs.append(parse_config_file(path))
        except OSError:
            continue
    return configs


def config_for_run(run: int, configs: List[ReductionConfig]) -> Optional[ReductionConfig]:
    """Return the config whose ``run_nums`` names this run, else the first config.

    Explicit membership wins; otherwise a lone config is assumed to apply. If
    several configs exist and none names the run, returns ``None`` so the
    caller can flag the run as unmapped.
    """
    for cfg in configs:
        if run in cfg.run_numbers:
            return cfg
    if len(configs) == 1 and not configs[0].run_numbers:
        return configs[0]
    return None


def discover_ipts(
    ipts: int,
    nexus_dir: str,
    shared_dir: str,
    reader: MetadataReader,
    runs_filter: Optional[List[int]] = None,
    instrument: str = "TOPAZ",
) -> IptsManifest:
    """Assemble the full discovery manifest for one IPTS."""
    nexus_map = find_nexus_files(nexus_dir, instrument=instrument)
    configs = find_reduction_configs(shared_dir)

    selected = sorted(nexus_map) if runs_filter is None else [r for r in sorted(nexus_map) if r in runs_filter]

    runs: List[RunInfo] = []
    run_config_map: Dict[int, str] = {}
    for run in selected:
        try:
            info = reader.read_run_metadata(nexus_map[run], run)
        except Exception as exc:
            info = RunInfo(run_number=run, nxs_path=nexus_map[run], error=str(exc))
        runs.append(info)
        cfg = config_for_run(run, configs)
        if cfg is not None:
            run_config_map[run] = cfg.source_path

    return IptsManifest(
        ipts=ipts,
        nexus_dir=nexus_dir,
        shared_dir=shared_dir,
        runs=runs,
        configs=configs,
        run_config_map=run_config_map,
    )
