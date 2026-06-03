"""Compatibility shim for the moved single-crystal newtabtemplate model (P2).

Re-exports ``exphub.techniques.single_crystal.models.newtabtemplate`` so existing
``exphub.app.models.newtabtemplate`` imports keep working during P2. Remove in P2.18.
"""

from ...techniques.single_crystal.models.newtabtemplate import *  # noqa: F401, F403
