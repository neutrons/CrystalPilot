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
        read back a value after setting it.
        """
        if snapshot_fn is None:
            return json.dumps({"parameter_name": parameter_name, "value": None, "error": "snapshot not available"})
        current = snapshot_fn()
        if parameter_name not in current:
            known = parameter_name in schema_props
            msg = "parameter exists in schema but has no bridged value" if known else "unknown parameter"
            return json.dumps({"parameter_name": parameter_name, "value": None, "error": msg})
        return json.dumps({"parameter_name": parameter_name, "value": current[parameter_name]})

    return [set_parameter, get_default_value, explain_parameter, get_parameter]
