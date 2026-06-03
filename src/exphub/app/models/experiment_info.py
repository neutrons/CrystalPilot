"""Compatibility shim for the moved single-crystal experiment-info model (P2.1).

Re-exports ``exphub.techniques.single_crystal.models.experiment_info`` so
existing ``exphub.app.models.experiment_info`` imports keep working during P2.
Remove in P2.18 once all importers point at the new location.
"""

from ...techniques.single_crystal.models.experiment_info import *  # noqa: F401, F403
