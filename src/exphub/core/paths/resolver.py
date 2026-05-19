"""Compose beamline-aware filesystem paths.

Two layers:

* :func:`ipts_name` — turn an IPTS number into the canonical ``IPTS-<n>``
  directory name. Idempotent if already prefixed.
* :class:`PathResolver` — bound to a beamline + IPTS, exposes properties for
  the common directories the app reads/writes (autoreduce, live monitor,
  EIC dropbox).

Use :func:`resolver_for` to construct one from the active beamline.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ..beamline import BeamlineContext, BeamlineSpec, active


def ipts_name(ipts: int | str) -> str:
    """Canonical IPTS directory name. Idempotent if ``ipts`` already starts with ``IPTS-``."""
    s = str(ipts).strip()
    if s.startswith("IPTS-"):
        return s
    return f"IPTS-{s}"


class PathResolver:
    """Bound to one (beamline, IPTS) pair.

    Every property returns a string path (not a :class:`Path`) because most
    consumers feed these to Mantid algorithms or write into Pydantic ``str``
    fields. Use ``Path(resolver.autoreduce_dir)`` at the call site if you
    want the object form.
    """

    def __init__(self, ctx: BeamlineContext, ipts: int | str | None = None):
        self.ctx = ctx
        self._ipts: Optional[str] = None if ipts in (None, "") else str(ipts)

    @property
    def spec(self) -> BeamlineSpec:
        return self.ctx.spec

    @property
    def ipts(self) -> str | None:
        return self._ipts

    @ipts.setter
    def ipts(self, value: int | str | None) -> None:
        self._ipts = None if value in (None, "") else str(value)

    # ----- roots ------------------------------------------------------------

    @property
    def shared_root(self) -> str:
        return self.spec.paths.shared_root

    @property
    def eic_dropbox_root(self) -> str:
        return self.spec.paths.eic_dropbox

    @property
    def default_calibration(self) -> str:
        return self.spec.paths.default_calibration

    # ----- IPTS-derived -----------------------------------------------------

    def _require_ipts(self) -> str:
        if not self._ipts:
            raise ValueError(
                f"PathResolver for {self.ctx.id!r} has no IPTS set; "
                "construct with ipts=... or assign .ipts before reading IPTS paths."
            )
        return ipts_name(self._ipts)

    @property
    def ipts_dir(self) -> str:
        return f"{self.shared_root}/{self._require_ipts()}"

    @property
    def autoreduce_dir(self) -> str:
        return f"{self.ipts_dir}/{self.spec.paths.autoreduce_subdir}"

    @property
    def live_monitor_dir(self) -> str:
        return f"{self.ipts_dir}/{self.spec.paths.live_monitor_subdir}"

    @property
    def eic_dropbox(self) -> str:
        return f"{self.eic_dropbox_root}/{self._require_ipts()}"

    # ----- convenience ------------------------------------------------------

    def ensure_dir(self, path: str) -> str:
        """``mkdir -p`` and return the path. Convenience for autoreduce / live-monitor
        directories that callers were previously creating ad hoc."""
        os.makedirs(path, exist_ok=True)
        return path


def resolver_for(ipts: int | str | None = None, beamline_id: str | None = None) -> PathResolver:
    """Construct a resolver bound to the active beamline (or a named one)."""
    if beamline_id is None:
        spec = active()
    else:
        from ..beamline import get  # local import to avoid cycle at module load
        spec = get(beamline_id)
    return PathResolver(BeamlineContext(spec), ipts=ipts)
