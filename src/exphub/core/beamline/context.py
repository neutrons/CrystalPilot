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
        gonio = self.spec.single_crystal.goniometer
        try:
            return gonio.angle_pvs[axis]
        except KeyError as exc:
            raise KeyError(
                f"Beamline {self.id!r} has no angle PV for axis {axis!r}. Known axes: {sorted(gonio.angle_pvs)}"
            ) from exc

    def ramp_pv(self, key: str) -> str:
        try:
            return self.spec.single_crystal.goniometer.ramp_pvs[key]
        except KeyError as exc:
            raise KeyError(f"Beamline {self.id!r} has no ramp PV for {key!r}.") from exc

    @property
    def charge_pv(self) -> str:
        return self.spec.single_crystal.goniometer.charge_pv

    @property
    def angle_columns(self) -> list[str]:
        """Ordered PV column names for the goniometer's angle axes."""
        gonio = self.spec.single_crystal.goniometer
        return [gonio.angle_pvs[axis] for axis in gonio.angle_columns_order]

    @property
    def angle_axis_keys(self) -> list[str]:
        """Internal axis names in the same order as :attr:`angle_columns`."""
        return list(self.spec.single_crystal.goniometer.angle_columns_order)

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
        cfg = self.spec.technique_config
        path = getattr(cfg, "bob_screen_path", None)
        if path is None:
            return None
        return self.spec.resolve(path)

    @property
    def bob_macros(self) -> Path | None:
        cfg = self.spec.technique_config
        path = getattr(cfg, "bob_macros_path", None)
        if path is None:
            return None
        return self.spec.resolve(path)

    @property
    def extra_subscribe_pvs(self) -> tuple[str, ...]:
        # Phoebus operator-screen assets are a single-crystal concern; a SANS
        # (or any non-single-crystal) technique_config has no such field, so the
        # app subscribes to nothing extra rather than crashing on access.
        cfg = self.spec.technique_config
        return tuple(getattr(cfg, "extra_subscribe_pvs", ()))
