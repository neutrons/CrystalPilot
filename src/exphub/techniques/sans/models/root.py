"""SANS technique root model (P4.2).

Composes the three SANS sub-models (sample/IPTS info, strategy table, I(Q)
reduction placeholder) into a single Pydantic root, mirroring the role the
single-crystal ``app/models/main_model.MainModel`` plays for that technique.

Kept as a small, self-contained composite so the SANS steering view-model can
bind each sub-model onto its own trame namespace exactly the way the
single-crystal steering VM binds ``model.experimentinfo`` / ``model.angleplan``
/ ``model.dataanalysis``. The shared EIC control model lives in ``core/eic`` and
is reused unchanged (every beamline submits through the same EIC pipeline; only
the row-builder differs — see ``MULTI_TECHNIQUE_PLAN.md`` decision #1).

This root is *additive*: P4.2 ships the SANS view-models + views, but the SANS
manifest (which would expose this via ``root_model_factory``) and the
mvvm_factory wiring land in later P4 / P5 steps. Nothing in ``app/`` imports
this yet.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ....core.eic import EICControlModel
from .ipts_info import SansIptsInfoModel
from .iq_reduction import SansIQReductionModel
from .strategy import SansStrategyModel


class SansMainModel(BaseModel):
    """Composite SANS technique model.

    Field names are chosen to read naturally for SANS while keeping the same
    binding idiom as the single-crystal root:

      - ``iptsinfo``     ← SANS analogue of single-crystal ``experimentinfo``
      - ``strategy``     ← SANS analogue of single-crystal ``angleplan``
      - ``iqreduction``  ← SANS analogue of single-crystal ``dataanalysis``
      - ``eiccontrol``   ← shared, unchanged (same name as single-crystal)
    """

    iptsinfo: SansIptsInfoModel = Field(default_factory=SansIptsInfoModel, title="SANS IPTS Info")
    strategy: SansStrategyModel = Field(default_factory=SansStrategyModel, title="SANS Strategy")
    iqreduction: SansIQReductionModel = Field(default_factory=SansIQReductionModel, title="SANS I(Q) Reduction")
    eiccontrol: EICControlModel = Field(default_factory=EICControlModel, title="EIC Control")
