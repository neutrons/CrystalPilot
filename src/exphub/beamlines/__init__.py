"""Beamline plug-ins.

Importing this package imports every sub-package, which registers each
beamline with :mod:`exphub.core.beamline.registry`.

Adding a new beamline: create ``beamlines/<id>/`` with a ``__init__.py`` that
imports its ``spec`` module — the spec module's import-time side effect calls
:func:`exphub.core.beamline.register`.
"""

from __future__ import annotations

# Importing each beamline package triggers its spec registration.
from . import topaz  # noqa: F401

__all__ = ["topaz"]
