"""CORELLI (SNS BL-9) beamline plug-in.

Importing this package registers the CORELLI spec with the core registry.
"""

from .spec import CORELLI

__all__ = ["CORELLI"]
