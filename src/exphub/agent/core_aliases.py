"""Small indirection module used by ``prompts.composer`` to break import cycles.

The composer can't import ``exphub.core.beamline`` directly without
the agent package pulling in the core+beamlines stack at module load time.
This file resolves the registry lazily on first call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.beamline import BeamlineSpec


def active_spec(beamline_id: str | None = None) -> BeamlineSpec:
    """Return the active or named beamline's spec, importing the registry lazily."""
    from ..core.beamline import active as _active
    from ..core.beamline import get as _get

    if beamline_id is None:
        return _active()
    return _get(beamline_id)
