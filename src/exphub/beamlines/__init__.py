"""Beamline plug-ins.

Importing this package imports every sub-package, which registers each
beamline with :mod:`exphub.core.beamline.registry`.

Adding a new beamline: create ``beamlines/<id>/`` with a ``__init__.py`` that
imports its ``spec`` module — the spec module's import-time side effect calls
:func:`exphub.core.beamline.register`.
"""

# ruff: noqa: I001 -- the import order below is intentional, not alphabetical:
# the first-imported beamline registers first and becomes the default ``active()``
# (see the note above the import). Letting isort sort it (corelli first) would
# silently change the default beamline back to CORELLI.
from __future__ import annotations

# Importing each beamline package triggers its spec registration.
# Order matters: the first registered beamline is the default ``active()``,
# so keep TOPAZ at the top until a launcher / selector overrides at runtime.
from . import (
    topaz,  # noqa: F401
    corelli,  # noqa: F401
    usans,  # noqa: F401
)

__all__ = ["topaz", "corelli", "usans"]
