"""TOPAZ (SNS BL-12) beamline plug-in.

Importing this package registers the TOPAZ spec with the core registry.
"""

from .spec import TOPAZ

__all__ = ["TOPAZ"]
