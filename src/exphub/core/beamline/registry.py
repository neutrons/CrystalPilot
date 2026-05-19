"""Beamline plug-in registry.

Discovery model: each ``src/exphub/beamlines/<id>/`` package's ``__init__``
calls :func:`register` with a :class:`BeamlineSpec` instance. Importing
``exphub.beamlines`` triggers registration of every shipped beamline.

The active beamline is tracked module-level for read-only convenience; the
authoritative source of truth is ``MainModel.beamline_id``. View-models and
the agent should obtain the active spec via :func:`active`.
"""

from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path

from .spec import BeamlineSpec

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, BeamlineSpec] = {}
_ACTIVE_ID: str | None = None


def register(spec: BeamlineSpec) -> BeamlineSpec:
    """Register a beamline spec. Idempotent: re-registering the same id replaces.

    Resolves ``spec.package_path`` from the caller's module file location if
    not already set, so plug-in authors don't have to wire it manually.
    """
    if spec.package_path is None:
        caller_frame = inspect.stack()[1]
        caller_file = Path(caller_frame.filename).resolve()
        spec.package_path = caller_file.parent
    _REGISTRY[spec.id] = spec
    logger.info("Registered beamline %r from %s", spec.id, spec.package_path)
    return spec


def get(beamline_id: str) -> BeamlineSpec:
    """Look up a registered beamline by id; raise KeyError if absent."""
    if beamline_id not in _REGISTRY:
        _discover()
    if beamline_id not in _REGISTRY:
        raise KeyError(
            f"Beamline {beamline_id!r} not registered. "
            f"Known: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[beamline_id]


def list_ids() -> list[str]:
    """Return all registered beamline ids in insertion order."""
    if not _REGISTRY:
        _discover()
    return list(_REGISTRY)


def set_active(beamline_id: str) -> BeamlineSpec:
    """Mark a beamline as active and return its spec."""
    global _ACTIVE_ID
    spec = get(beamline_id)
    _ACTIVE_ID = beamline_id
    return spec


def active() -> BeamlineSpec:
    """Return the currently active beamline spec.

    Falls back to the *first-registered* beamline (insertion order) if
    :func:`set_active` has not been called. Raises if no beamlines are
    registered at all.

    Beamline plug-ins should arrange their import order so the intended
    default lands first; see ``src/exphub/beamlines/__init__.py``.
    """
    if _ACTIVE_ID is not None:
        return _REGISTRY[_ACTIVE_ID]
    if not _REGISTRY:
        _discover()
    if not _REGISTRY:
        raise RuntimeError(
            "No beamlines registered. Import exphub.beamlines first."
        )
    return next(iter(_REGISTRY.values()))


def _discover() -> None:
    """Import the ``exphub.beamlines`` package, triggering plug-in registration."""
    try:
        importlib.import_module("exphub.beamlines")
    except ImportError as exc:
        logger.warning("exphub.beamlines not importable (%s) — registry empty", exc)


def _reset_for_tests() -> None:
    """Test-only helper. Clear registry state."""
    global _ACTIVE_ID
    _REGISTRY.clear()
    _ACTIVE_ID = None
