"""Compatibility shim for the moved single-crystal angle_plan_engine model (P2).

Re-exports ``exphub.techniques.single_crystal.models.angle_plan_engine`` so existing
``exphub.app.models.angle_plan_engine`` imports keep working during P2. Remove in P2.18.
"""

from ...techniques.single_crystal.models.angle_plan_engine import *  # noqa: F401, F403
