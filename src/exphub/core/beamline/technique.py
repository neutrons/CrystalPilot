"""Technique-family plug-in contract.

A *technique* (single-crystal diffraction, SANS, reflectometry, ...) owns the
*shape* of an experiment: which tabs exist and what they look like, the agent's
phase machine and action verbs, the prompt/RAG corpus, and the root data model.
A *beamline* plugs into exactly one technique and only supplies per-instrument
parameters (PVs, paths) plus optional tab overrides.

This module is the technique-side mirror of :mod:`exphub.core.beamline.spec` /
:mod:`exphub.core.beamline.registry`:

- :class:`TechniqueManifest` — the data a technique package populates.
- :class:`TabKey` — string tab identifiers (replaces the legacy 1/2/3/5/6 ints
  at the manifest + agent layers; the trame dispatcher keeps using ints).
- :class:`PhaseDefinition`, :class:`ActionTool` — the agent-side contract a
  technique declares (consumed once the agent is parametrised in P1.b).
- :func:`register_technique`, :func:`get_technique`, :func:`active_technique` —
  the registry surface, with lazy ``importlib`` discovery of
  ``exphub.techniques.<id>`` on first access.

Per ``MULTI_TECHNIQUE_PLAN.md`` this layer is introduced additively in P1: no
single-crystal code has moved yet, so the single-crystal manifest lazy-imports
the existing views from ``app/views/``.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from .spec import TabFactory

logger = logging.getLogger(__name__)


class TabKey(str, Enum):
    """Stable string identifiers for the five tab slots.

    Replaces the legacy integer tab numbers (1, 2, 3, 5, 6 — note the gap at 4)
    at the manifest and agent layers. The trame ``v_if``/``v_show`` predicates
    in the dispatcher keep addressing tabs by int; translation happens there.
    """

    IPTS = "ipts"
    LIVE = "live"
    STEERING = "steering"
    STATUS = "status"
    ANALYSIS = "analysis"


@dataclass(frozen=True)
class PhaseDefinition:
    """One step of a technique's experiment workflow (for the PhaseManager).

    The agent's ``PhaseManager`` is parametrised from a technique's phase list
    in P1.b; this is the cross-technique contract for an entry. ``field_prefixes``
    scopes which schema fields are relevant while the user is in this phase.
    """

    name: str
    tab: TabKey
    description: str
    field_prefixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActionTool:
    """A technique-specific agent verb exposed to the chat view-model.

    The chat VM's action-function table is built from the active manifest in
    P1.b; ``handler`` is resolved against the live view-model at wiring time
    (kept as a dotted name / callable so the manifest stays import-cheap).
    """

    name: str
    description: str = ""
    handler: Callable[..., Any] | None = None


class TechniqueManifest(BaseModel):
    """Everything a technique family contributes to the app.

    The single plug-in point for a technique. Beamlines never re-declare any of
    this; they select a technique via :attr:`BeamlineSpec.technique` and, at
    most, override individual tabs through :class:`BeamlineSpec.tabs`.

    Fields populated in P1.a: ``id``, ``display_name``, ``default_tabs`` (tabs
    1-3), ``tab_labels``, ``tab_aliases``, ``bridged_submodels``. The remaining
    agent-side fields are part of the locked contract but are wired to their
    consumers in P1.b (phases → PhaseManager, action_tools → chat VM,
    prompts_dir → composer, root_model_factory / eic_row_builder → P1.b/P3a).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    id: str
    display_name: str
    default_tabs: dict[TabKey, TabFactory] = Field(default_factory=dict)
    optional_tab_defaults: dict[TabKey, TabFactory] = Field(default_factory=dict)
    tab_labels: dict[TabKey, str] = Field(default_factory=dict)
    tab_aliases: dict[str, TabKey] = Field(default_factory=dict)
    bridged_submodels: tuple[str, ...] = ()
    phases: tuple[PhaseDefinition, ...] = ()
    action_tools: tuple[ActionTool, ...] = ()
    prompts_dir: Path | None = None
    knowledge_dir: Path | None = None
    eic_row_builder: Callable[..., Any] | None = None
    root_model_factory: Callable[[], Any] | None = None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_TECHNIQUE_REGISTRY: dict[str, TechniqueManifest] = {}


def register_technique(manifest: TechniqueManifest) -> TechniqueManifest:
    """Register a technique manifest. Idempotent: re-registering replaces."""
    _TECHNIQUE_REGISTRY[manifest.id] = manifest
    logger.info("Registered technique %r", manifest.id)
    return manifest


def get_technique(technique_id: str) -> TechniqueManifest:
    """Look up a technique manifest, lazily importing its package on first use.

    Discovery model mirrors the beamline registry: importing
    ``exphub.techniques.<id>`` triggers that package's ``register_technique``
    call. Raises :class:`KeyError` if the package is missing or doesn't register.
    """
    if technique_id not in _TECHNIQUE_REGISTRY:
        try:
            importlib.import_module(f"exphub.techniques.{technique_id}")
        except ModuleNotFoundError as exc:
            raise KeyError(
                f"Technique {technique_id!r} not registered and "
                f"exphub.techniques.{technique_id} is not importable."
            ) from exc
    if technique_id not in _TECHNIQUE_REGISTRY:
        raise KeyError(
            f"Importing exphub.techniques.{technique_id} did not register a "
            f"manifest. Known: {sorted(_TECHNIQUE_REGISTRY)}"
        )
    return _TECHNIQUE_REGISTRY[technique_id]


def list_technique_ids() -> list[str]:
    """Return the ids of every already-registered technique (no discovery)."""
    return list(_TECHNIQUE_REGISTRY)


def active_technique() -> TechniqueManifest:
    """Return the manifest for the active beamline's technique family."""
    from .registry import active

    return get_technique(active().technique)


def _reset_for_tests() -> None:
    """Test-only helper. Clear registry state."""
    _TECHNIQUE_REGISTRY.clear()


__all__ = [
    "ActionTool",
    "PhaseDefinition",
    "TabKey",
    "TechniqueManifest",
    "active_technique",
    "get_technique",
    "list_technique_ids",
    "register_technique",
]
