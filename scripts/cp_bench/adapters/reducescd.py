"""Real reducer: run ReduceSCD on the full run and the pre-cutoff window.

Mechanism (see CP_BENCH_PLAN §4/§7, "the hard part"):

* **full** — invoke ``ReduceSCD_Parallel.py`` with a cloned config whose
  ``data_directory`` points at the (read-only) ``/SNS`` nexus dir.
* **partial** — first slice ``[0, t_cut]`` with ``FilterByTimeStop`` and save
  the events into the *writable* benchmark dir, then invoke the **unchanged**
  reducer against that dir. Only the time window differs between the two runs.

Everything is written under ``out_dir`` (guarded — never ``/SNS``); ``/SNS`` is
only ever read. The save algorithm and filename pattern are parameters because
the stock reducer's loader convention must be confirmed on the server (the one
integration seam flagged in the plan). Unit tests use a fake ``Reducer``.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
from typing import Any, Dict, Optional

from ..compare import parse_isaw_integrate, read_isaw_lattice
from ..models import ReductionConfig, ReductionResult
from ..safety import assert_writable, safe_makedirs, safe_write_text

_RUN_RE = re.compile(r"_(\d+)\.nxs(?:\.h5)?$", re.IGNORECASE)


class ReduceSCDReducer:
    """Invoke the ReduceSCD driver for full and partial windows."""

    def __init__(
        self,
        reducer_script: str,
        python_exe: str = sys.executable,
        instrument: str = "TOPAZ",
        timeout_s: float = 7200.0,
        save_algorithm: str = "SaveNexusProcessed",
        filename_pattern: str = "{instrument}_{run}.nxs.h5",
    ) -> None:
        self.reducer_script = reducer_script
        self.python_exe = python_exe
        self.instrument = instrument
        self.timeout_s = timeout_s
        self.save_algorithm = save_algorithm
        self.filename_pattern = filename_pattern

    def reduce(
        self,
        nxs_path: str,
        cfg: ReductionConfig,
        out_dir: str,
        time_stop_s: Optional[float],
        label: str,
    ) -> ReductionResult:
        """Reduce full (``time_stop_s is None``) or partial (``[0, time_stop_s]``)."""
        writable = safe_makedirs(out_dir)
        run = self._run_number(nxs_path)

        if time_stop_s is None:
            data_dir = os.path.dirname(nxs_path)  # read-only /SNS dir; reducer only reads it
        else:
            data_dir = self._preslice(nxs_path, float(time_stop_s), writable, run)

        config_path = self._write_config(cfg, writable, data_dir, run)
        returncode = self._invoke(config_path, writable)
        return self._collect(writable, label, returncode)

    # ------------------------------------------------------------------ #
    def _run_number(self, nxs_path: str) -> int:
        match = _RUN_RE.search(os.path.basename(nxs_path))
        return int(match.group(1)) if match else 0

    def _preslice(self, nxs_path: str, time_stop_s: float, out_dir: str, run: int) -> str:
        """Save events in ``[0, time_stop_s]`` into ``out_dir``; return that dir."""
        import mantid.simpleapi as mtdapi

        dest_name = self.filename_pattern.format(instrument=self.instrument, run=run)
        dest = assert_writable(os.path.join(out_dir, dest_name))
        ws: Any = mtdapi.LoadEventNexus(
            Filename=nxs_path,
            FilterByTimeStop=time_stop_s,
            OutputWorkspace="_cpbench_slice",
        )
        getattr(mtdapi, self.save_algorithm)(InputWorkspace=ws, Filename=dest)
        mtdapi.DeleteWorkspace("_cpbench_slice")
        return out_dir

    def _write_config(self, cfg: ReductionConfig, out_dir: str, data_dir: str, run: int) -> str:
        """Clone the discovered config, overriding only I/O + run window."""
        values: Dict[str, str] = dict(cfg.values)
        values["output_directory"] = out_dir
        values["data_directory"] = data_dir
        values["run_nums"] = str(run)
        text = "".join(f"{key} {value}\n" for key, value in values.items())
        return safe_write_text(os.path.join(out_dir, "reduce.config"), text)

    def _invoke(self, config_path: str, out_dir: str) -> int:
        """Run the reducer as a subprocess; capture its log into ``out_dir``."""
        try:
            proc = subprocess.run(
                [self.python_exe, self.reducer_script, config_path],
                cwd=out_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
            log = (proc.stdout or "") + "\n----- stderr -----\n" + (proc.stderr or "")
            returncode = proc.returncode
        except subprocess.TimeoutExpired as exc:
            log = f"reducer timed out after {self.timeout_s}s: {exc}"
            returncode = -1
        safe_write_text(os.path.join(out_dir, "reduce.log"), log)
        return returncode

    def _collect(self, out_dir: str, label: str, returncode: int) -> ReductionResult:
        """Locate the produced ``.integrate``/``.mat`` and summarise them."""
        integrate = _first(glob.glob(os.path.join(out_dir, "*.integrate")))
        ub = _first(glob.glob(os.path.join(out_dir, "*.mat")))
        result = ReductionResult(
            label=label,
            output_dir=out_dir,
            integrate_path=integrate,
            ub_path=ub,
            returncode=returncode,
        )
        if integrate:
            result.num_peaks = len(parse_isaw_integrate(integrate))
        if ub:
            result.lattice = read_isaw_lattice(ub)
        if returncode != 0 and not integrate:
            result.error = f"reducer exit {returncode}, no .integrate produced (see reduce.log)"
        return result


def _first(paths: list[str]) -> str:
    """Return the first path (sorted) or an empty string."""
    return sorted(paths)[0] if paths else ""
