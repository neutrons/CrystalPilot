"""Beamline plug-in contract.

A concrete beamline populates a :class:`BeamlineSpec`. Everything downstream
(PV catalog, path resolver, agent prompt assembler, tab manifest) reads from
this single object so adding a new beamline never requires editing the
framework.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field


class GoniometerSpec(BaseModel):
    """Sample-environment rotation stack."""

    type: Literal[
        "ambient_2axis",
        "cryo_1axis",
        "eulerian_4axis",
        "other",
    ] = "ambient_2axis"
    angle_pvs: dict[str, str] = Field(
        default_factory=dict,
        description='Axis name → EPICS PV. E.g. {"omega": "BL12:Mot:goniokm:omega"}',
    )
    ramp_pvs: dict[str, str] = Field(
        default_factory=dict,
        description="Temperature-ramp PVs (start/end/rate/soak/run); optional.",
    )
    charge_pv: str = Field(
        default="",
        description='Detector charge threshold PV used for "wait_for=PCharge" rows.',
    )
    angle_columns_order: list[str] = Field(
        default_factory=list,
        description="Display order of axes in the plan table.",
    )


class DetectorSpec(BaseModel):
    """Area-detector / status-screen description."""

    bob_screen_path: Path | None = Field(
        default=None,
        description="Phoebus .bob file (relative to the beamline package).",
    )
    macros_path: Path | None = Field(default=None)
    extra_subscribe_pvs: list[str] = Field(
        default_factory=list,
        description="PVs not in the .bob screen that still need a JS subscription.",
    )
    detector_layout: str = "generic"
    pixel_dims: tuple[int, int] | None = None


class MantidSpec(BaseModel):
    """Mantid-side defaults for live reduction and peak finding."""

    instrument_name: str = ""
    wavelength_min: float = 0.0
    wavelength_max: float = 0.0
    default_max_q: float = 10.0
    default_tolerance: float = 0.12
    default_num_peaks_to_find: int = 200


class PathsSpec(BaseModel):
    """File-system roots; everything is composed from these."""

    shared_root: str = ""
    eic_dropbox: str = ""
    default_calibration: str = ""
    autoreduce_subdir: str = "shared/autoreduce"
    live_monitor_subdir: str = "shared/CrystalPilot/live-data-monitoring"


class EICSpec(BaseModel):
    beamline_code: str = ""
    is_simulation_default: bool = False
    supports_simulation: bool = True
    write_scope: list[str] = Field(default_factory=lambda: ["EIC:write"])


class AgentSpec(BaseModel):
    """Per-beamline agent assets."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    context_prompt: Path | None = None
    knowledge_dir: Path | None = None
    presets: dict[str, dict[str, Any]] = Field(default_factory=dict)
    supported_tasks: list[str] = Field(
        default_factory=lambda: ["experiment_steering", "app_help"]
    )


class TabOverrides(BaseModel):
    """Plug-in points for per-tab content.

    Each attribute is either ``None`` (use the framework's default tab) or a
    callable that builds the tab's view. The callable contract is intentionally
    loose so beamlines can mix Pydantic models and Vuetify layouts in whatever
    way fits.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    experiment_info: Callable[..., Any] | None = None
    angle_plan: Callable[..., Any] | None = None
    temporal_analysis: Callable[..., Any] | None = None
    css_status: Callable[..., Any] | None = None
    data_analysis: Callable[..., Any] | None = None


class BeamlineSpec(BaseModel):
    """One beamline's full description.

    Concrete beamlines live under ``src/exphub/beamlines/<id>/spec.py`` and
    register an instance of this class with :mod:`exphub.core.beamline.registry`.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    display_name: str
    facility: Literal["SNS", "HFIR", "ILL", "ISIS", "ESS", "other"] = "SNS"
    target_station: str | None = None
    package_path: Path | None = Field(
        default=None,
        description="Filesystem root of this beamline's plug-in package; "
        "resolved automatically when registered.",
    )
    goniometer: GoniometerSpec = Field(default_factory=GoniometerSpec)
    detector: DetectorSpec = Field(default_factory=DetectorSpec)
    mantid: MantidSpec = Field(default_factory=MantidSpec)
    paths: PathsSpec = Field(default_factory=PathsSpec)
    eic: EICSpec = Field(default_factory=EICSpec)
    agent: AgentSpec = Field(default_factory=AgentSpec)
    tabs: TabOverrides = Field(default_factory=TabOverrides)

    def resolve(self, relative: Path) -> Path:
        """Resolve a path declared in this spec against the beamline package root."""
        if relative.is_absolute() or self.package_path is None:
            return relative
        return self.package_path / relative
