"""Beamline plug-in contracts.

Public surface:

- :class:`BeamlineSpec`, :class:`GoniometerSpec`, :class:`DetectorSpec`,
  :class:`MantidSpec`, :class:`PathsSpec`, :class:`EICSpec`, :class:`AgentSpec`,
  :class:`TabOverrides` — the data classes a concrete beamline populates.
- :class:`SingleCrystalConfig`, :class:`SansConfig` — the discriminated
  ``technique_config`` payloads, keyed on ``kind``.
- :func:`register`, :func:`get`, :func:`list_ids`, :func:`active` — the
  module-level beamline registry surface.
- :class:`BeamlineContext` — the runtime accessor handed to view-models and
  the agent.
- :class:`TechniqueManifest`, :class:`TabKey`, :class:`PhaseDefinition`,
  :class:`ActionTool` + :func:`register_technique`, :func:`get_technique`,
  :func:`active_technique` — the technique-family plug-in surface.
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
from .technique import (
    ActionTool,
    PhaseDefinition,
    TabKey,
    TechniqueManifest,
    active_technique,
    get_technique,
    list_technique_ids,
    register_technique,
)

__all__ = [
    "ActionTool",
    "AgentSpec",
    "BeamlineContext",
    "BeamlineSpec",
    "DetectorSpec",
    "EICSpec",
    "GoniometerSpec",
    "MantidSpec",
    "PathsSpec",
    "PhaseDefinition",
    "SansConfig",
    "SingleCrystalConfig",
    "TabKey",
    "TabOverrides",
    "TechniqueConfig",
    "TechniqueManifest",
    "active",
    "active_technique",
    "get",
    "get_technique",
    "list_ids",
    "list_technique_ids",
    "register",
    "register_technique",
    "set_active",
]
