"""Compatibility shim for the moved single-crystal data-analysis view (P2).

The module moved under ``exphub.techniques.single_crystal.views``; this
re-export keeps existing ``exphub.app.views`` imports working during P2.
Remove in P2.18 once all importers point at the new location.
"""

from ...techniques.single_crystal.views.data_analysis import *  # noqa: F401, F403
