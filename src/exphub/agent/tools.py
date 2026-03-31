"""LangChain tools for the CrystalPilot agent.

Tools are created via ``make_tools(schema_props)`` which closes over the
schema dict — no global mutable state.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def make_tools(schema_props: dict[str, dict], snapshot_fn=None) -> list:
    """Return a list of LangChain tools bound to *schema_props*.

    Parameters
    ----------
    schema_props:
        Flat ``{field_name: schema_info}`` dict generated from the Pydantic models.
    snapshot_fn:
        Optional zero-argument callable that returns the current flat config dict
        (i.e. ``bridge.snapshot_models`` partially applied with the live model).
        Required for the ``get_parameter`` tool to work at runtime.
    """

    @tool
    def set_parameter(parameter_name: str, parameter_value: Any) -> dict:
        """Record a configuration value provided by the user.

        Call this tool whenever the user provides a value for ANY CrystalPilot
        configuration field (experiment info, angle plan, EIC control, etc.).
        """
        logger.debug("set_parameter called: %s = %s", parameter_name, parameter_value)
        return {"parameter_name": parameter_name, "parameter_value": parameter_value}

    @tool
    def get_default_value(parameter_name: str) -> str:
        """Return the schema default for a parameter as a JSON string."""
        info = schema_props.get(parameter_name, {})
        return json.dumps({"parameter_name": parameter_name, "default": info.get("default")})

    @tool
    def explain_parameter(parameter_name: str) -> str:
        """Return the human-readable description of a parameter from its schema."""
        info = schema_props.get(parameter_name)
        if info and "description" in info:
            return info["description"]
        if info and "title" in info:
            return f"{info['title']} (no additional description available)."
        return f"Sorry, I don't have a description for '{parameter_name}'."

    @tool
    def get_parameter(parameter_name: str) -> str:
        """Return the current live value of a configuration parameter from the UI.

        Use this to confirm what is already set before asking the user, or to
        read back a value after setting it.  The response also includes
        ``valid_options`` when the field has a known set of choices.
        """
        if snapshot_fn is None:
            return json.dumps({"parameter_name": parameter_name, "value": None, "error": "snapshot not available"})
        current = snapshot_fn()
        if parameter_name not in current:
            known = parameter_name in schema_props
            msg = "parameter exists in schema but has no bridged value" if known else "unknown parameter"
            return json.dumps({"parameter_name": parameter_name, "value": None, "error": msg})
        result: dict = {"parameter_name": parameter_name, "value": current[parameter_name]}
        # Attach valid choices when available (schema enum or live option list)
        info = schema_props.get(parameter_name, {})
        if info.get("enum"):
            result["valid_options"] = info["enum"]
        else:
            for suffix in ("_list", "_options"):
                opt_key = parameter_name + suffix
                opt_val = current.get(opt_key)
                if isinstance(opt_val, list) and opt_val and all(isinstance(v, str) for v in opt_val):
                    result["valid_options"] = opt_val
                    break
        return json.dumps(result, default=str)

    @tool
    def list_parameters(group: str = "") -> str:
        """List all settable configuration parameters.

        Returns a JSON array of objects with ``name``, ``title``, ``type``,
        optional ``description``, and optional ``options`` (valid choices for
        dropdown/select fields).

        Pass a keyword in *group* to filter results by field name or title
        (case-insensitive substring match).  Leave empty to list everything.

        Use this before setting a value to discover valid field names and
        allowed choices.
        """
        # Re-enrich with live option lists so the result reflects current state
        live_props: dict = {}
        for key, info in schema_props.items():
            live_props[key] = dict(info)

        if snapshot_fn is not None:
            snap = snapshot_fn()
            for key, value in snap.items():
                if not isinstance(value, list) or not value or not all(isinstance(v, str) for v in value):
                    continue
                if key.endswith("_list"):
                    field = key[:-5]
                elif key.endswith("_options"):
                    field = key[:-8]
                else:
                    continue
                if field in live_props:
                    live_props[field] = {**live_props[field], "enum": value}

        params = []
        for key, info in live_props.items():
            entry: dict = {
                "name": key,
                "title": info.get("title", key),
                "type": info.get("type", "string"),
            }
            if info.get("enum"):
                entry["options"] = info["enum"]
            if info.get("description"):
                entry["description"] = info["description"]
            params.append(entry)

        if group:
            gl = group.lower()
            params = [p for p in params if gl in p["name"].lower() or gl in p["title"].lower()]

        return json.dumps(params, default=str)

    return [set_parameter, get_default_value, explain_parameter, get_parameter, list_parameters]
