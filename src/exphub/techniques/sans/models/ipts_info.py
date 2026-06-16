"""SANS sample / IPTS info model (P4.1 skeleton).

The SANS analogue of the single-crystal
:class:`~exphub.techniques.single_crystal.models.experiment_info.ExperimentInfoModel`,
reduced to *sample-info fields only*. SANS has no crystal lattice, so every
crystallography field from the single-crystal model is intentionally absent:

  - no ``crystalsystem`` / ``point_group`` / ``centering``
  - no ``UB`` matrix / ``UBFileName`` / ``read_ub``
  - no d-spacing / peak-finding / satellite-peak parameters

What remains is the shared experiment-identity surface (experiment name, IPTS
number, instrument). Field titles/defaults mirror the single-crystal model so the
IPTS-Info tab view can be built with the same idioms.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from ....core.beamline import active as _active_beamline
from ....core.beamline import get as _beamline_get
from ....core.beamline import list_ids as _beamline_ids


def _default_instrument_list() -> List[str]:
    """Return the Mantid instrument names of every registered SANS beamline.

    Mirrors the single-crystal helper but reads the SANS technique config. Any
    beamline whose ``technique`` is not ``"sans"`` (or whose config lacks a
    mantid instrument name) is skipped. Falls back to ``[""]`` so the dropdown
    is never empty.
    """
    try:
        names: List[str] = []
        for bid in _beamline_ids():
            spec = _beamline_get(bid)
            inst = _sans_instrument_name(spec)
            if inst:
                names.append(inst)
        return names or [""]
    except Exception:
        return [""]


def _default_instrument() -> str:
    try:
        return _sans_instrument_name(_active_beamline())
    except Exception:
        return ""


def _sans_instrument_name(spec: object) -> str:
    """Best-effort Mantid instrument name from a beamline spec's SANS config.

    Provisional: the SANS technique config shape is not finalized (P5 ships the
    first real SANS beamline / USANS spec). We probe a couple of likely
    attribute paths and degrade to ``""`` so importing this model never fails
    on a single-crystal-only registry.
    """
    sans = getattr(spec, "sans", None)
    if sans is None:
        return ""
    mantid = getattr(sans, "mantid", None)
    if mantid is not None:
        return getattr(mantid, "instrument_name", "") or ""
    return getattr(sans, "instrument_name", "") or ""


class SansIptsInfoModel(BaseModel):
    """SANS sample / experiment identity (sample-info fields only).

    Deliberately excludes all single-crystal crystallography: no crystal
    system, point group, centering, UB matrix, or d-spacing. SANS reduces to an
    azimuthally-averaged I(Q), so none of the reciprocal-lattice machinery
    applies.
    """

    exp_name: str = Field(
        default="test",
        title="Experiment Name",
        description="Used to create a directory in the shared folder under the IPTS directory.",
    )
    ipts_number: str = Field(
        default="35036",
        title="IPTS Number",
        min_length=1,
        description="Proposal number for the experiment.",
    )
    instrument: str = Field(
        default_factory=_default_instrument,
        title="Instrument Name",
    )

    error_message: str = ""
    show_error: bool = False

    class Options(BaseModel):
        """Dropdown option lists for the SANS IPTS-Info tab."""

        instrument_list: List[str] = Field(default_factory=_default_instrument_list)

    options: "SansIptsInfoModel.Options" = Field(default_factory=lambda: SansIptsInfoModel.Options())

    def get_ipts_name(self) -> str:
        """Return the canonical ``IPTS-<n>`` form of the IPTS number."""
        if self.ipts_number.startswith("IPTS"):
            return self.ipts_number
        return f"IPTS-{self.ipts_number}"

    def clear_error(self) -> None:
        self.error_message = ""
        self.show_error = False

    def reset(self) -> None:
        default_model = SansIptsInfoModel()
        for field, value in default_model:
            setattr(self, field, value)
