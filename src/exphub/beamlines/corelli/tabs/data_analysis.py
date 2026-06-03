"""CORELLI Data Analysis tab (tab 6 / ANALYSIS).

Thin per-beamline wrapper around the shared single-crystal
:class:`DataAnalysisView`. CORELLI is a single-crystal beamline whose ANALYSIS
slot has *no* unconditional technique default — the manifest only offers the
data-analysis launcher as an *optional* default (``optional_tab_defaults``).
Without an explicit factory here the dispatcher's fall-through would render the
generic placeholder (see ``app/views/tab_content_panel.py``), so CORELLI ships
this factory and registers it on ``CORELLI.tabs.analysis`` to guarantee the
real launcher renders.

The shared view already adapts to the active beamline (e.g. it only shows the
"Data Reduction" button when the spec declares an ``external_links["data_reduction"]``
URL, which CORELLI does not yet), so no CORELLI-specific UI is required today.
This wrapper is the seam for any future CORELLI-only analysis controls.
"""

from __future__ import annotations

from typing import Any


def build_data_analysis(view_model: Any) -> Any:
    """Factory matching the ``TabFactory`` protocol.

    Lazy-imports the technique view so spec registration stays import-cheap and
    the trame view stack only loads when the tab is first navigated to.
    """
    from ....techniques.single_crystal.views.data_analysis import DataAnalysisView

    return DataAnalysisView(view_model)
