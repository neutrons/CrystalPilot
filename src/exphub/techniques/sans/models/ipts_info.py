"""SANS sample / IPTS info model (P4.1 skeleton).

The SANS analogue of the single-crystal
:class:`~exphub.techniques.single_crystal.models.experiment_info.ExperimentInfoModel`,
reduced to *sample-info fields only*. SANS has no crystal lattice, so every
crystallography field from the single-crystal model is intentionally absent:

  - no ``crystalsystem`` / ``point_group`` / ``centering``
  - no ``UB`` matrix / ``UBFileName`` / ``read_ub``
  - no d-spacing / peak-finding / satellite-peak parameters

What remains is the shared experiment-identity surface (experiment name, IPTS
number). The Mantid instrument name is derived from the active beamline at submit
time (``active().mantid_instrument_name``), not a user field. Field
titles/defaults mirror the single-crystal model so the IPTS-Info tab view can be
built with the same idioms.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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
    error_message: str = ""
    show_error: bool = False

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
