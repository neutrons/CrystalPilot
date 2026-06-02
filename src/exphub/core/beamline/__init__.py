"""Beamline plug-in contracts.

Public surface:

- :class:`BeamlineSpec`, :class:`GoniometerSpec`, :class:`DetectorSpec`,
  :class:`MantidSpec`, :class:`PathsSpec`, :class:`EICSpec`, :class:`AgentSpec`,
  :class:`TabOverrides` — the data classes a concrete beamline populates.
- :class:`SingleCrystalConfig`, :class:`SansConfig` — the discriminated
  ``technique_config`` payloads, keyed on ``kind``.
- :func:`register`, :func:`get`, :func:`list_ids`, :func:`active` — the
  module-level registry surface.
- :class:`BeamlineContext` — the runtime accessor handed to view-models and
  the agent.
"""

from .context import BeamlineContext
from .registry import active, get, list_ids, register, set_active
from .spec import (
    AgentSpec,
    BeamlineSpec,
    DetectorSpec,
    EICSpec,
    GoniometerSpec,
    MantidSpec,
    PathsSpec,
    SansConfig,
    SingleCrystalConfig,
    TabOverrides,
    TechniqueConfig,
)

__all__ = [
    "AgentSpec",
    "BeamlineContext",
    "BeamlineSpec",
    "DetectorSpec",
    "EICSpec",
    "GoniometerSpec",
    "MantidSpec",
    "PathsSpec",
    "SansConfig",
    "SingleCrystalConfig",
    "TabOverrides",
    "TechniqueConfig",
    "active",
    "get",
    "list_ids",
    "register",
    "set_active",
]
