"""Live-data tab: Mantid orchestration + figure builders.

Public surface re-exported here so existing imports
``from ..models.temporal_analysis import TemporalAnalysisModel`` continue
to resolve. Submodules:

- :mod:`.workflow`   — :class:`MantidWorkflow`: StartLiveData + per-cycle state
- :mod:`.pipeline`   — the 5 per-cycle phases (checkpoint, load, refine, integrate, check)
- :mod:`.selectors`  — peak-selection strategies (All Peaks, Max Peak, ...)
- :mod:`.figures`    — pure plotly figure builders
- :mod:`.model`      — :class:`TemporalAnalysisModel`: pydantic binding surface
"""

from .model import TemporalAnalysisModel
from .selectors import (
    SELECTOR_REGISTRY,
    AllPeaksSelector,
    MaxPeakSelector,
    PeakSelector,
    SelectionResult,
    make_selector,
)
from .workflow import MantidWorkflow

__all__ = [
    "TemporalAnalysisModel",
    "MantidWorkflow",
    "PeakSelector",
    "SelectionResult",
    "AllPeaksSelector",
    "MaxPeakSelector",
    "SELECTOR_REGISTRY",
    "make_selector",
]
