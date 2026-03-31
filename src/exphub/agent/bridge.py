"""Bidirectional parameter bridge between the Agent and CrystalPilot models.

Agent → UI:  ``apply_agent_config`` takes the agent's flat config_state dict
             and writes matching fields into the Pydantic sub-models, then
             pushes the updated models into the Trame view via their bindings.

UI → Agent:  ``snapshot_models`` reads current Pydantic model values and
             returns a flat dict the agent can use as its config_state.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Sub-model attribute names on MainModel that the agent can read and write.
# Import this constant in mvvm_factory and view_models/chat instead of
# re-listing the names by hand.
BRIDGED_SUBMODELS: tuple[str, ...] = ("experimentinfo", "angleplan", "eiccontrol", "dataanalysis")


def snapshot_models(main_model: BaseModel) -> Dict[str, Any]:
    """Return a flat dict of all bridged fields from the current model state.

    Field names are kept as-is (e.g. ``ipts_number``, ``crystalsystem``).
    """
    flat: Dict[str, Any] = {}
    for attr_name in BRIDGED_SUBMODELS:
        sub = getattr(main_model, attr_name, None)
        if sub is None:
            continue
        for field_name in sub.model_fields:
            val = getattr(sub, field_name, None)
            # Skip complex nested models / options objects
            if isinstance(val, BaseModel):
                continue
            flat[field_name] = val
    return flat


def apply_agent_config(
    config_state: Dict[str, Any],
    main_model: BaseModel,
    bindings: Dict[str, Any],
) -> list[str]:
    """Write agent config_state values into the matching Pydantic sub-models.

    Parameters
    ----------
    config_state
        Flat dict from the agent (``{field_name: value}``).
    main_model
        The ``MainModel`` instance.
    bindings
        Mapping of sub-model attribute name → its ``TrameBinding``, e.g.
        ``{"experimentinfo": vm.experimentinfo_bind, ...}``.

    Returns
    -------
    list[str]
        Names of fields that were successfully updated.
    """
    updated: list[str] = []

    for attr_name in BRIDGED_SUBMODELS:
        sub = getattr(main_model, attr_name, None)
        if sub is None:
            continue
        bind = bindings.get(attr_name)
        dirty = False

        for field_name in sub.model_fields:
            if field_name not in config_state:
                continue
            new_val = config_state[field_name]
            old_val = getattr(sub, field_name, None)
            if new_val == old_val:
                continue
            try:
                setattr(sub, field_name, new_val)
                updated.append(field_name)
                dirty = True
                logger.debug("bridge: %s.%s = %r", attr_name, field_name, new_val)
            except Exception as exc:
                logger.warning("bridge: failed to set %s.%s: %s", attr_name, field_name, exc)

        if dirty and bind is not None:
            try:
                bind.update_in_view(sub)
            except Exception as exc:
                logger.warning("bridge: failed to push %s to view: %s", attr_name, exc)

    return updated
