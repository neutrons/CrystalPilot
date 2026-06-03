"""Small-angle neutron scattering (SANS) technique family.

Importing this package registers the SANS
:class:`~exphub.core.beamline.technique.TechniqueManifest`. Triggered lazily by
``get_technique("sans")`` (the lazy-import side effect), exactly like the
single-crystal package. The manifest (P4.3) wires the SANS data-models (P4.1),
view-models + views (P4.2), agent phases, prompt fragment, and EIC row-builder
into the technique plug-in surface.
"""

from .manifest import SANS  # noqa: F401 — registers on import

