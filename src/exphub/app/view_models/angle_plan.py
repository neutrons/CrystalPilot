"""Compatibility shim for the moved single-crystal angle-plan view-model (P2).

Re-exports the technique-package view-model so existing app-side imports
(notably ``angleplan_optimize``, lazily imported by the steering view-model)
keep working during P2. Remove in P2.18.
"""

from ...techniques.single_crystal.view_models.angle_plan import *  # noqa: F401, F403
