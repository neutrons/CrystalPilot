"""Compatibility shim for the moved single-crystal css_status model (P2).

Re-exports ``exphub.techniques.single_crystal.models.css_status`` so existing
``exphub.app.models.css_status`` imports keep working during P2. Remove in P2.18.
"""

from ...techniques.single_crystal.models.css_status import *  # noqa: F401, F403
