"""Runtime accessor for the active beamline.

View-models, the agent, and any code that needs PVs/paths/presets receives a
:class:`BeamlineContext` rather than importing the spec directly. This keeps
the call sites read-only and lets a single switch operation update everything.
"""

from __future__ import annotations

from pathlib import Path

from .spec import BeamlineSpec


class BeamlineContext:
    """Thin facade over a :class:`BeamlineSpec`."""

    def __init__(self, spec: BeamlineSpec):
        self.spec = spec

    # ----- identity ---------------------------------------------------------

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def display_name(self) -> str:
        return self.spec.display_name

    # ----- PVs --------------------------------------------------------------

    def angle_pv(self, axis: str) -> str:
        try:
            return self.spec.goniometer.angle_pvs[axis]
        except KeyError as exc:
            raise KeyError(
                f"Beamline {self.id!r} has no angle PV for axis {axis!r}. "
                f"Known axes: {sorted(self.spec.goniometer.angle_pvs)}"
            ) from exc

    def ramp_pv(self, key: str) -> str:
        try:
            return self.spec.goniometer.ramp_pvs[key]
        except KeyError as exc:
            raise KeyError(
                f"Beamline {self.id!r} has no ramp PV for {key!r}."
            ) from exc

    @property
    def charge_pv(self) -> str:
        return self.spec.goniometer.charge_pv

    @property
    def angle_columns(self) -> list[str]:
        """Ordered PV column names for the goniometer's angle axes."""
        order = self.spec.goniometer.angle_columns_order
        return [self.spec.goniometer.angle_pvs[axis] for axis in order]

    @property
    def angle_axis_keys(self) -> list[str]:
        """Internal axis names in the same order as :attr:`angle_columns`."""
        return list(self.spec.goniometer.angle_columns_order)

    # ----- paths ------------------------------------------------------------

    def ipts_root(self, ipts: int | str) -> str:
        return f"{self.spec.paths.shared_root}/IPTS-{ipts}"

    def autoreduce_dir(self, ipts: int | str) -> str:
        return f"{self.ipts_root(ipts)}/{self.spec.paths.autoreduce_subdir}"

    def live_monitor_dir(self, ipts: int | str) -> str:
        return f"{self.ipts_root(ipts)}/{self.spec.paths.live_monitor_subdir}"

    def eic_dropbox_dir(self, ipts: int | str) -> str:
        return f"{self.spec.paths.eic_dropbox}/IPTS-{ipts}"

    # ----- files ------------------------------------------------------------

    @property
    def bob_screen(self) -> Path | None:
        if self.spec.detector.bob_screen_path is None:
            return None
        return self.spec.resolve(self.spec.detector.bob_screen_path)

    @property
    def bob_macros(self) -> Path | None:
        if self.spec.detector.macros_path is None:
            return None
        return self.spec.resolve(self.spec.detector.macros_path)

    @property
    def extra_subscribe_pvs(self) -> tuple[str, ...]:
        return tuple(self.spec.detector.extra_subscribe_pvs)
