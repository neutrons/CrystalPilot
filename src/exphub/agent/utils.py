"""Shared utilities for the CrystalPilot agent."""

from __future__ import annotations

from typing import Any


def coerce_type(value: Any, field_info: dict) -> Any:
    """Coerce a raw value into the type declared in the JSON schema."""
    t = field_info.get("type")
    if t == "array":
        if isinstance(value, (list, tuple)):
            return list(value)
        if isinstance(value, str):
            parts = [v.strip() for v in (value.split(",") if "," in value else value.split()) if v.strip()]
            items_type = field_info.get("items", {}).get("type")
            if items_type == "number":
                return [float(v) for v in parts]
            if items_type == "integer":
                return [int(float(v)) for v in parts]
            return parts
        return [value]
    if t == "number":
        return float(value)
    if t == "integer":
        return int(float(value))
    if t == "boolean":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "yes", "y", "1")
    if t == "string":
        return str(value)
    return value


def pretty_name(key: str, schema_props: dict) -> str:
    """Return a human-readable label for a schema field key."""
    info = schema_props.get(key, {})
    return info.get("title") or key.replace("_", " ").title()
