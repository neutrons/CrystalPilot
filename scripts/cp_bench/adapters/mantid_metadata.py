"""Real metadata reader: experiment info from a NeXus file via Mantid (read-only).

Loads metadata only (no events), so it is cheap even across many runs. Makes no
writes. Validated on the analysis server; not exercised in unit tests (those use
a fake ``MetadataReader``).
"""

from __future__ import annotations

from typing import Any

from ..models import RunInfo


class MantidMetadataReader:
    """Extract :class:`RunInfo` from a NeXus event file using Mantid."""

    def __init__(self, instrument: str = "TOPAZ") -> None:
        self.instrument = instrument

    def read_run_metadata(self, nxs_path: str, run_number: int) -> RunInfo:
        """Return experiment info for one run; failures are captured, not raised."""
        info = RunInfo(run_number=run_number, nxs_path=nxs_path, instrument=self.instrument)
        try:
            import mantid.simpleapi as mtdapi

            ws: Any = mtdapi.LoadEventNexus(
                Filename=nxs_path,
                MetaDataOnly=True,
                LoadMonitors=False,
                OutputWorkspace="_cpbench_meta",
            )
            run = ws.getRun()
            start = run.startTime()
            end = run.endTime()
            start_s = start.totalNanoseconds() * 1e-9
            end_s = end.totalNanoseconds() * 1e-9
            info.start_time = start.toISO8601String()
            info.end_time = end.toISO8601String()
            info.duration_s = max(0.0, end_s - start_s)
            try:
                info.total_proton_charge = float(run.getProtonCharge())
            except Exception:
                info.total_proton_charge = 0.0
            info.title = str(ws.getTitle() or "")
            try:
                info.sample_name = str(ws.sample().getName() or "")
            except Exception:
                info.sample_name = ""
            mtdapi.DeleteWorkspace("_cpbench_meta")
        except Exception as exc:
            info.error = f"metadata read failed: {exc}"
        return info
