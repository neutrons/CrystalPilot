"""Utilities for auto-generating a flat JSON-schema property map from CrystalPilot Pydantic models.

The Agent uses this schema to validate user inputs and to display field
descriptions/defaults when prompting.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Type

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def _flatten_json_schema(schema: dict, prefix: str = "") -> Dict[str, dict]:
    """Recursively flatten a Pydantic v2 JSON-schema ``properties`` map.

    Nested ``$defs`` / sub-models are expanded so every leaf field becomes a
    top-level key (with no prefix, to keep names flat and agent-friendly).
    """
    defs = schema.get("$defs", {})
    props: Dict[str, dict] = {}

    for key, info in schema.get("properties", {}).items():
        # If the property is a $ref → resolve once
        ref = info.get("$ref") or info.get("allOf", [{}])[0].get("$ref")
        if ref:
            ref_name = ref.rsplit("/", 1)[-1]
            sub_schema = defs.get(ref_name, {})
            # recurse into the sub-model
            props.update(_flatten_json_schema({**sub_schema, "$defs": defs}))
            continue

        # Skip computed / read-only fields
        if info.get("readOnly"):
            continue

        # Skip internal housekeeping fields
        if key.startswith("_") or key in ("options", "error_message", "show_error"):
            continue

        props[key] = info

    return props


def schema_from_pydantic(model_cls: Type[BaseModel]) -> Dict[str, dict]:
    """Return a flat {field_name: schema_info} dict for a Pydantic v2 model.

    This mirrors the structure that NeuDiff-Agent's ``load_schema_properties``
    returns from a hand-written JSON schema, but is generated automatically.
    """
    raw = model_cls.model_json_schema()
    return _flatten_json_schema(raw)


def schema_from_model_instance(model: BaseModel) -> Dict[str, dict]:
    """Convenience: call ``schema_from_pydantic`` on the instance's class."""
    return schema_from_pydantic(type(model))
