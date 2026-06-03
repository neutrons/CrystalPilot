"""Compatibility shim for the moved single-crystal data_analysis model (P2).

Re-exports ``exphub.techniques.single_crystal.models.data_analysis`` so existing
``exphub.app.models.data_analysis`` imports keep working during P2. Remove in P2.18.
"""

from ...techniques.single_crystal.models.data_analysis import *  # noqa: F401, F403
