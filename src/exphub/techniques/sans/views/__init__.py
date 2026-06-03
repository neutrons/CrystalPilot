"""SANS tab views (P4.2).

Tab 1 (IPTS info), tab 2 (I(Q) reduction / live placeholder), tab 3 (strategy),
in the SANS shape. Mirror the single-crystal tab views' construction idiom (a
view class taking the steering VM and connecting its ``*_bind`` surface) so a
future SANS manifest can wire them as default tab factories.
"""

from .ipts_info import SansIptsInfoView
from .iq_reduction import SansIQReductionView
from .strategy import SansStrategyView

__all__ = [
    "SansIptsInfoView",
    "SansIQReductionView",
    "SansStrategyView",
]
