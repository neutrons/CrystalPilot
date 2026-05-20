"""Peak-selection strategies for the live-data tab.

The tab plots a single scalar (``intensity_ratio``) versus time. What that
scalar means depends on the user's pick in the ``Peak Selection`` dropdown.
Each strategy here implements one mapping from (precomputed peak intensities
+ statistics) to a :class:`SelectionResult`.

New modes (individual-peak intensity, peak ratio, ...) are added by writing
a new selector class and registering it in :data:`SELECTOR_REGISTRY`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

import numpy as np


@dataclass
class SelectionResult:
    """What the figures need to plot, per cycle.

    ``intensity_ratio`` drives the top figure; ``rsig`` drives the bottom
    one. ``aux`` is an open dict that future selectors can populate with
    extra series (per-peak intensities, ratio history, ...); the legacy
    selectors leave it empty.
    """

    intensity_ratio: float
    rsig: float
    aux: dict[str, Any] = field(default_factory=dict)


class PeakSelector(Protocol):
    """Strategy interface invoked once per live-reduction cycle."""

    name: str

    def select(
        self,
        peaks_ws: Any,
        int_array: np.ndarray,
        sig_array: np.ndarray,
        max_peak_idx: int,
        statistics: dict,
    ) -> SelectionResult: ...


class AllPeaksSelector:
    """Mean I/σ(I) across the indexed peaks workspace.

    Reads the statistics row that the pipeline already produces via
    ``StatisticsOfPeaksWorkspace`` — cheap.
    """

    name = "All Peaks"

    def select(
        self,
        peaks_ws: Any,
        int_array: np.ndarray,
        sig_array: np.ndarray,
        max_peak_idx: int,
        statistics: dict,
    ) -> SelectionResult:
        r = float(statistics["Mean ((I)/sd(I))"])
        return SelectionResult(intensity_ratio=r, rsig=100.0 / r)


class MaxPeakSelector:
    """I/σ of the brightest peak in the current cycle.

    ``max_peak_idx`` is tracked across cycles by the pipeline; this
    selector just reads it.
    """

    name = "Max Peak"

    def select(
        self,
        peaks_ws: Any,
        int_array: np.ndarray,
        sig_array: np.ndarray,
        max_peak_idx: int,
        statistics: dict,
    ) -> SelectionResult:
        r = float(int_array[max_peak_idx] / sig_array[max_peak_idx])
        return SelectionResult(intensity_ratio=r, rsig=100.0 / r)


SelectorFactory = Callable[..., PeakSelector]

# Adding a new mode = register a class here. Keys must match the dropdown
# option strings in ``TemporalAnalysisModel.data_selection_options``.
SELECTOR_REGISTRY: dict[str, SelectorFactory] = {
    "All Peaks": lambda **_: AllPeaksSelector(),
    "Max Peak": lambda **_: MaxPeakSelector(),
}


def make_selector(name: str, **params: Any) -> Optional[PeakSelector]:
    """Build a selector for the named mode, or return ``None``.

    Returning ``None`` for unknown modes preserves the legacy fall-through:
    dropdown options like ``Bragg Peaks`` / ``Satellite Peaks`` /
    ``Diffuse scattering`` had no branch in the original switch and silently
    left ``intensity_ratio`` at its previous value.
    """
    factory = SELECTOR_REGISTRY.get(name)
    if factory is None:
        return None
    return factory(**params)
