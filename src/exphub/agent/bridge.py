"""Bidirectional parameter bridge between the Agent and CrystalPilot models.

Agent → UI:  ``apply_agent_config`` takes the agent's flat config_state dict
             and writes matching fields into the Pydantic sub-models, then
             pushes the updated models into the Trame view via their bindings.

UI → Agent:  ``snapshot_models`` reads current Pydantic model values and
             returns a flat dict the agent can use as its config_state.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, get_args, get_origin

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Sub-model attribute names on MainModel that the agent can read and write.
# Import this constant in mvvm_factory and view_models/chat instead of
# re-listing the names by hand.
BRIDGED_SUBMODELS: tuple[str, ...] = ("experimentinfo", "angleplan", "eiccontrol", "dataanalysis")


def _coerce_list_field(model_cls: type, field_name: str, value: Any) -> Any:
    """Coerce *value* to ``List[T]`` if the field annotation requires it.

    When the agent sets a ``List[BaseModel]`` field (e.g. ``angle_list_pd``)
    via a list of plain dicts, Pydantic won't auto-convert without
    ``validate_assignment=True``.  This helper converts each dict element to
    the declared item type explicitly.
    """
    if not isinstance(value, list):
        return value
    field = model_cls.model_fields.get(field_name)
    if field is None or get_origin(field.annotation) is not list:
        return value
    args = get_args(field.annotation)
    if not args:
        return value
    item_cls = args[0]
    if not (isinstance(item_cls, type) and issubclass(item_cls, BaseModel)):
        return value
    return [item_cls(**item) if isinstance(item, dict) else item for item in value]


def snapshot_models(main_model: BaseModel) -> Dict[str, Any]:
    """Return a flat dict of all bridged fields from the current model state.

    Field names are kept as-is (e.g. ``ipts_number``, ``crystalsystem``).
    """
    flat: Dict[str, Any] = {}
    for attr_name in BRIDGED_SUBMODELS:
        sub = getattr(main_model, attr_name, None)
        if sub is None:
            continue
        for field_name in type(sub).model_fields:
            val = getattr(sub, field_name, None)
            if isinstance(val, BaseModel):
                # Expand the `options` sub-model so option lists are visible
                # in the snapshot (e.g. instrument_list, crystalsystem_list).
                if field_name == "options":
                    for opt_field in type(val).model_fields:
                        flat[opt_field] = getattr(val, opt_field, None)
                continue
            flat[field_name] = val
    return flat


def apply_agent_config(
    config_state: Dict[str, Any],
    main_model: BaseModel,
    bindings: Dict[str, Any],
) -> tuple[list[str], dict[str, str]]:
    """Write agent config_state values into the matching Pydantic sub-models.

    Parameters
    ----------
    config_state
        Flat dict from the agent (``{field_name: value}``).
    main_model
        The ``MainModel`` instance.
    bindings
        Mapping of sub-model attribute name → its ``TrameBinding``.

    Returns
    -------
    updated : list[str]
        Names of fields that were successfully written to the model.
    errors : dict[str, str]
        Mapping of ``field_name → error message`` for fields that failed
        Pydantic validation. The caller should surface these to the agent.
    """
    updated: list[str] = []
    errors: dict[str, str] = {}

    for attr_name in BRIDGED_SUBMODELS:
        sub = getattr(main_model, attr_name, None)
        if sub is None:
            continue
        bind = bindings.get(attr_name)
        dirty = False

        for field_name in type(sub).model_fields:
            if field_name not in config_state:
                continue
            new_val = config_state[field_name]
            old_val = getattr(sub, field_name, None)
            if new_val == old_val:
                continue
            try:
                new_val = _coerce_list_field(type(sub), field_name, new_val)
                setattr(sub, field_name, new_val)
                updated.append(field_name)
                dirty = True
                print(f"[Bridge] SET {attr_name}.{field_name} = {new_val!r} (was {old_val!r})")
            except Exception as exc:
                errors[field_name] = str(exc)
                print(f"[Bridge] FAIL {attr_name}.{field_name}: {exc}")
                logger.warning("bridge: failed to set %s.%s: %s", attr_name, field_name, exc)

        if dirty and bind is not None:
            try:
                bind.update_in_view(sub)
                print(f"[Bridge] Pushed {attr_name} to view")
            except Exception as exc:
                print(f"[Bridge] PUSH FAILED {attr_name}: {exc}")
                logger.warning("bridge: failed to push %s to view: %s", attr_name, exc)

    return updated, errors
