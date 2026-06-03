"""Compatibility shim for the moved single-crystal angle-plan view (P2).

The module moved under ``exphub.techniques.single_crystal.views``; this
re-export keeps existing ``exphub.app.views`` imports working during P2.
Remove in P2.18 once all importers point at the new location.
"""

from ...techniques.single_crystal.views.angle_plan import *  # noqa: F401, F403
