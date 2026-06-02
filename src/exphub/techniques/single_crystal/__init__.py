"""Single-crystal diffraction technique family.

Importing this package registers the single-crystal
:class:`~exphub.core.beamline.technique.TechniqueManifest`. Triggered lazily by
``get_technique("single_crystal")``.
"""

from .manifest import SINGLE_CRYSTAL  # noqa: F401 — registers on import
