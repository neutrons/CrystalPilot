"""Technique-family implementations.

Each ``exphub.techniques.<id>`` package registers a
:class:`exphub.core.beamline.technique.TechniqueManifest` from its ``__init__``.
Discovery is lazy: :func:`exphub.core.beamline.technique.get_technique` imports
``exphub.techniques.<id>`` on first access, which triggers registration. Nothing
is imported here eagerly, so ``import exphub.techniques`` stays cheap.

See ``MULTI_TECHNIQUE_PLAN.md`` for the technique vs beamline boundary.
"""
