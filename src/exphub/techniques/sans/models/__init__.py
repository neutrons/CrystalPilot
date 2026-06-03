"""SANS data models (P4.1 skeleton).

Mirror the *structure* of the single-crystal equivalents but in a SANS shape:

- :mod:`.ipts_info` — sample-info fields only (no crystal system / point group /
  centering / UB / d-spacing).
- :mod:`.strategy` — CSV-loadable editable strategy table; single-crystal
  strategy-CSV row shape (Title/Comment/Wait For/Value) with SANS column names
  (provisional; see module docstring).
- :mod:`.iq_reduction` — I(Q) reduction placeholder; the prediction-model
  dropdown stays ``"TBD"`` until a real SANS pipeline is specified.
"""

from .ipts_info import SansIptsInfoModel
from .iq_reduction import SansIQReductionModel
from .strategy import SansStrategyModel, SansStrategyRow

__all__ = [
    "SansIptsInfoModel",
    "SansIQReductionModel",
    "SansStrategyModel",
    "SansStrategyRow",
]
