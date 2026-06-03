"""Compatibility shim for the moved single-crystal angle-plan model (P2).

The module moved under ``exphub.techniques.single_crystal.models``; this
re-export keeps existing ``exphub.app.models`` imports working during P2.
Remove in P2.18 once all importers point at the new location.
"""

from ...techniques.single_crystal.models.angle_plan import *  # noqa: F401, F403
