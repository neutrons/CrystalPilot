"""USANS (SNS BL-1A) beamline plug-in.

Importing this package registers the USANS spec with the core registry. USANS
is the first ``technique="sans"`` beamline shipped with ExpHub; adding it
required zero edits to framework code (``core/``, ``app/``, ``agent/``) — the
registry auto-discovers this package via ``beamlines/__init__.py`` and the
SANS technique manifest supplies the tab shapes / agent contract.
"""

from .spec import USANS

__all__ = ["USANS"]
