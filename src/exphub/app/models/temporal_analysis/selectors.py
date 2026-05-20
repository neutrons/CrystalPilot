"""Peak-selection strategies for the live-data tab.

The tab plots a single scalar (``intensity_ratio``) versus time. What that
scalar means depends on the user's pick in the ``Peak Selection`` dropdown.
Each strategy here implements one mapping from (precomputed peak intensities
+ statistics) to a :class:`SelectionResult`.

Selectors may also override the figure titles + y-axis labels by populating
the optional label fields on :class:`SelectionResult`; this lets modes like
``Peak Ratio`` (whose y-axis is no longer "Signal Noise Ratio") render with
their own labels without leaking mode-specific code into :mod:`.figures`.

Adding a new mode = register a class in :data:`SELECTOR_REGISTRY`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, Sequence

import numpy as np


@dataclass
class SelectionResult:
    """What the figures need to plot, per cycle.

    ``intensity_ratio`` drives the top figure; ``rsig`` drives the bottom
    one. ``aux`` is an open dict that selectors can populate with extra
    per-cycle context (matched peak index, per-peak intensities, ...).
    The four ``*_title`` / ``*_yaxis`` fields, when set, override the
    figures' default labels for this mode.
    """

    intensity_ratio: float
    rsig: float
    aux: dict[str, Any] = field(default_factory=dict)

    # Optional label overrides. None → figures use their defaults.
    intensity_title: Optional[str] = None
    intensity_yaxis: Optional[str] = None
    uncertainty_title: Optional[str] = None
    uncertainty_yaxis: Optional[str] = None


class PeakSelector(Protocol):
    """Strategy interface invoked once per live-reduction cycle.

    Implementations may return ``None`` to signal "skip this cycle" —
    the pipeline will not append to the plot buffers and figures will
    keep their previous frame (or, for explicit placeholder modes,
    the model can substitute a "Waiting for data" figure).
    """

    name: str

    def select(
        self,
        peaks_ws: Any,
        int_array: np.ndarray,
        sig_array: np.ndarray,
        max_peak_idx: int,
        statistics: dict,
    ) -> Optional[SelectionResult]: ...


# ---------- helpers ----------

def _mnp_is_zero(peak: Any) -> bool:
    """True if a peak's modulation indices (m,n,p) are all zero.

    Tolerates Mantid versions / workspaces that pre-date ``getIntMNP``;
    when the call is unavailable, peaks are treated as Bragg.
    """
    getter = getattr(peak, "getIntMNP", None)
    if getter is None:
        return True
    try:
        mnp = getter()
    except Exception:
        return True
    return all(int(m) == 0 for m in (mnp[0], mnp[1], mnp[2]))


def _find_peak_by_inthkl(
    peaks_ws: Any, target: Sequence[int]
) -> Optional[int]:
    """Linear scan for the peak whose ``getIntHKL`` matches ``target``.

    Returns the workspace-row index, or ``None`` if no match.
    """
    th, tk, tl = int(target[0]), int(target[1]), int(target[2])
    n = peaks_ws.getNumberPeaks()
    for i in range(n):
        peak = peaks_ws.getPeak(i)
        ihkl = peak.getIntHKL()
        if int(ihkl[0]) == th and int(ihkl[1]) == tk and int(ihkl[2]) == tl:
            return i
    return None


def _reduce_mean_isig(
    int_array: np.ndarray,
    sig_array: np.ndarray,
    idxs: Sequence[int],
) -> Optional[tuple[float, float]]:
    """Mean(I/σ) over the indexed subset. Returns ``None`` if empty.

    Output: ``(intensity_ratio, rsig)`` with ``rsig = 100 / intensity_ratio``.
    """
    if not idxs:
        return None
    ints = int_array[list(idxs)]
    sigs = sig_array[list(idxs)]
    # Guard against zero sigmas (peaks with no statistical content)
    mask = sigs > 0
    if not np.any(mask):
        return None
    r = float(np.mean(ints[mask] / sigs[mask]))
    if r == 0:
        return None
    return r, 100.0 / r


# ---------- selector classes ----------

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
    ) -> Optional[SelectionResult]:
        r = float(statistics["Mean ((I)/sd(I))"])
        return SelectionResult(intensity_ratio=r, rsig=100.0 / r)


class BraggPeaksSelector:
    """Mean I/σ over peaks whose modulation indices are all zero."""

    name = "Bragg Peaks"

    def select(
        self,
        peaks_ws: Any,
        int_array: np.ndarray,
        sig_array: np.ndarray,
        max_peak_idx: int,
        statistics: dict,
    ) -> Optional[SelectionResult]:
        idxs = [i for i in range(peaks_ws.getNumberPeaks())
                if _mnp_is_zero(peaks_ws.getPeak(i))]
        out = _reduce_mean_isig(int_array, sig_array, idxs)
        if out is None:
            return None
        r, rsig = out
        return SelectionResult(
            intensity_ratio=r,
            rsig=rsig,
            aux={"n_peaks": len(idxs)},
            intensity_title="Prediction of Mean I/σ (Bragg)",
            intensity_yaxis="Mean I/σ (Bragg)",
            uncertainty_title="Prediction of σ(I)/I (Bragg)",
            uncertainty_yaxis="σ(I)/I (Bragg) (%)",
        )


class SatellitePeaksSelector:
    """Mean I/σ over peaks whose modulation indices are non-zero.

    Requires the pipeline's ``IndexPeaks`` to be configured with modulation
    vectors + ``MaxOrder`` — otherwise every peak has ``IntMNP == (0,0,0)``
    and this selector reports "no satellite peaks indexed yet".
    """

    name = "Satellite Peaks"

    def select(
        self,
        peaks_ws: Any,
        int_array: np.ndarray,
        sig_array: np.ndarray,
        max_peak_idx: int,
        statistics: dict,
    ) -> Optional[SelectionResult]:
        idxs = [i for i in range(peaks_ws.getNumberPeaks())
                if not _mnp_is_zero(peaks_ws.getPeak(i))]
        out = _reduce_mean_isig(int_array, sig_array, idxs)
        if out is None:
            return None
        r, rsig = out
        return SelectionResult(
            intensity_ratio=r,
            rsig=rsig,
            aux={"n_peaks": len(idxs)},
            intensity_title="Prediction of Mean I/σ (Satellite)",
            intensity_yaxis="Mean I/σ (Satellite)",
            uncertainty_title="Prediction of σ(I)/I (Satellite)",
            uncertainty_yaxis="σ(I)/I (Satellite) (%)",
        )


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
    ) -> Optional[SelectionResult]:
        if max_peak_idx < 0 or sig_array[max_peak_idx] <= 0:
            return None
        r = float(int_array[max_peak_idx] / sig_array[max_peak_idx])
        return SelectionResult(intensity_ratio=r, rsig=100.0 / r)


class DiffuseScatteringSelector:
    """Placeholder mode — always returns None (figures show "Waiting for data").

    Real implementation will replace this once the diffuse-scattering
    reduction pipeline is specified.
    """

    name = "Diffuse Scattering"

    def select(
        self,
        peaks_ws: Any,
        int_array: np.ndarray,
        sig_array: np.ndarray,
        max_peak_idx: int,
        statistics: dict,
    ) -> Optional[SelectionResult]:
        return None


class IndividualPeakSelector:
    """I/σ of the single peak matching the user-entered HKL."""

    name = "Individual Peak"

    def __init__(self, hkl: Sequence[int]) -> None:
        self.hkl = (int(hkl[0]), int(hkl[1]), int(hkl[2]))

    def select(
        self,
        peaks_ws: Any,
        int_array: np.ndarray,
        sig_array: np.ndarray,
        max_peak_idx: int,
        statistics: dict,
    ) -> Optional[SelectionResult]:
        idx = _find_peak_by_inthkl(peaks_ws, self.hkl)
        if idx is None:
            print(f"IndividualPeakSelector: peak {self.hkl} not found in workspace")
            return None
        if sig_array[idx] <= 0:
            return None
        r = float(int_array[idx] / sig_array[idx])
        title = f"Prediction of I/σ — peak {self.hkl}"
        return SelectionResult(
            intensity_ratio=r,
            rsig=100.0 / r,
            aux={"matched_idx": idx, "hkl": self.hkl,
                 "I": float(int_array[idx]), "sigma": float(sig_array[idx])},
            intensity_title=title,
            intensity_yaxis=f"I/σ at {self.hkl}",
            uncertainty_title=f"Prediction of σ/I — peak {self.hkl}",
            uncertainty_yaxis=f"σ(I)/I at {self.hkl} (%)",
        )


class PeakRatioSelector:
    """Raw intensity ratio I_a / I_b with propagated relative uncertainty.

    Top figure y = ``I_a / I_b``. Bottom figure y = σ(ratio)/ratio × 100,
    computed as ``√((σ_a/I_a)² + (σ_b/I_b)²)``.
    """

    name = "Peak Ratio"

    def __init__(self, hkl_a: Sequence[int], hkl_b: Sequence[int]) -> None:
        self.hkl_a = (int(hkl_a[0]), int(hkl_a[1]), int(hkl_a[2]))
        self.hkl_b = (int(hkl_b[0]), int(hkl_b[1]), int(hkl_b[2]))

    def select(
        self,
        peaks_ws: Any,
        int_array: np.ndarray,
        sig_array: np.ndarray,
        max_peak_idx: int,
        statistics: dict,
    ) -> Optional[SelectionResult]:
        ia = _find_peak_by_inthkl(peaks_ws, self.hkl_a)
        ib = _find_peak_by_inthkl(peaks_ws, self.hkl_b)
        if ia is None or ib is None:
            missing = []
            if ia is None: missing.append(str(self.hkl_a))
            if ib is None: missing.append(str(self.hkl_b))
            print(f"PeakRatioSelector: peaks not found: {', '.join(missing)}")
            return None
        I_a, s_a = float(int_array[ia]), float(sig_array[ia])
        I_b, s_b = float(int_array[ib]), float(sig_array[ib])
        if I_b == 0 or I_a == 0 or s_a <= 0 or s_b <= 0:
            return None
        ratio = I_a / I_b
        rel_unc = ((s_a / I_a) ** 2 + (s_b / I_b) ** 2) ** 0.5
        return SelectionResult(
            intensity_ratio=ratio,
            rsig=rel_unc * 100.0,
            aux={
                "hkl_a": self.hkl_a, "hkl_b": self.hkl_b,
                "I_a": I_a, "sigma_a": s_a,
                "I_b": I_b, "sigma_b": s_b,
            },
            intensity_title=f"Peak intensity ratio {self.hkl_a} / {self.hkl_b}",
            intensity_yaxis="I_a / I_b",
            uncertainty_title=f"Propagated σ(ratio)/ratio — {self.hkl_a} / {self.hkl_b}",
            uncertainty_yaxis="σ(ratio) / ratio (%)",
        )


SelectorFactory = Callable[..., PeakSelector]

# Adding a new mode = register a class here. Keys must match the dropdown
# option strings in ``TemporalAnalysisModel.data_selection_options``.
SELECTOR_REGISTRY: dict[str, SelectorFactory] = {
    "All Peaks": lambda **_: AllPeaksSelector(),
    "Bragg Peaks": lambda **_: BraggPeaksSelector(),
    "Satellite Peaks": lambda **_: SatellitePeaksSelector(),
    "Max Peak": lambda **_: MaxPeakSelector(),
    "Diffuse Scattering": lambda **_: DiffuseScatteringSelector(),
    "Individual Peak": lambda hkl=(1, 0, 0), **_: IndividualPeakSelector(hkl),
    "Peak Ratio": lambda hkl_a=(1, 0, 0), hkl_b=(0, 1, 0), **_: PeakRatioSelector(hkl_a, hkl_b),
}


def make_selector(name: str, **params: Any) -> Optional[PeakSelector]:
    """Build a selector for the named mode, or return ``None``.

    Unknown names return ``None`` (legacy fall-through behavior for
    dropdown values without a registered handler).
    """
    factory = SELECTOR_REGISTRY.get(name)
    if factory is None:
        return None
    return factory(**params)
