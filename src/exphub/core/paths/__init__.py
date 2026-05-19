"""Path resolution against the active beamline.

Replaces hardcoded ``/SNS/<instrument>/IPTS-{n}/...`` strings sprinkled
across the codebase with calls that compose paths from
``BeamlineSpec.paths``.
"""

from .resolver import PathResolver, ipts_name, resolver_for

__all__ = ["PathResolver", "ipts_name", "resolver_for"]
