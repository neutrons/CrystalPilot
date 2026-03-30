"""CrystalPilot conversational agent.

Builds a LangGraph graph that:
1. Receives user messages
2. Calls the LLM (with tools bound)
3. Validates tool results (set_parameter, explain, default)
4. Returns a reply string

The agent is *schema-driven*: it receives a flat property map generated from
CrystalPilot's Pydantic models to validate every ``set_parameter`` call.
"""

from __future__ import annotations

import json
import logging
from textwrap import dedent
from typing import Any, Set

from jsonschema import ValidationError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph

from .llm import get_configured_chat_model
from .state import AgentState
from .tools import get_all_tools

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ helpers

SYSTEM_PROMPT = dedent("""\
You are CrystalPilot Assistant, an AI helper for single-crystal neutron
diffraction experiments at ORNL beamlines.

Your capabilities:
- Guide users through experiment configuration (IPTS info, reduction
  parameters, angle plans, etc.)
- Explain what each parameter means and what its default is.
- Set parameter values when the user provides them.
- Answer general crystallography and beamline questions.

When the user provides a value for a configuration field, ALWAYS call the
`set_parameter` tool with the appropriate parameter_name and parameter_value.

When the user asks what a parameter means, call `explain_parameter`.
When the user asks for the default, call `get_default_value`.

Be concise and helpful. Use Markdown for formatting.
""")


def _coerce_type(value: Any, field_info: dict) -> Any:
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
        s = str(value).lower()
        return s in ("true", "yes", "y", "1")
    return value


def _pretty(key: str, schema_props: dict) -> str:
    info = schema_props.get(key, {})
    return info.get("title") or key.replace("_", " ").title()


# ================================================================= Agent

class Agent:
    """CrystalPilot LangGraph agent."""

    def __init__(self, schema_properties: dict[str, dict]) -> None:
        # Populate the global that tools.get_default_value reads
        import exphub.agent.tools as _tools_mod
        _tools_mod._SCHEMA_PROPERTIES = schema_properties

        self.schema_properties = schema_properties
        self._answered: Set[str] = set()
        self._config_state: dict[str, Any] = {}
        self._in_config_mode = False
        self.graph = self._build_graph()

    # ------------------------------------------------------------ graph build

    def _build_graph(self):
        tools = get_all_tools()

        def call_model(state: AgentState):
            msgs = [SystemMessage(content=SYSTEM_PROMPT)]

            cfg_state = state.get("config_state", {})
            if state.get("in_config_mode"):
                ctx = f"CONTEXT: Current config values: {json.dumps(cfg_state, default=str)}"
                msgs.append(SystemMessage(content=ctx))

            msgs.extend(state["messages"][-6:])

            llm = get_configured_chat_model().bind_tools(tools)
            out = llm.invoke(msgs)
            return {
                "messages": [out],
                "config_state": state.get("config_state", {}),
                "in_config_mode": state.get("in_config_mode", False),
                "nudge_count": state.get("nudge_count", 0),
            }

        def handle_tool_result(state: AgentState):
            tool_msg = state["messages"][-1]
            if not isinstance(tool_msg, ToolMessage):
                return state

            try:
                tool_output = json.loads(tool_msg.content)
            except (json.JSONDecodeError, TypeError):
                tool_output = tool_msg.content

            reply = ""

            if tool_msg.name == "explain_parameter":
                return {
                    "messages": [AIMessage(content=str(tool_output))],
                    "config_state": state["config_state"],
                    "in_config_mode": state["in_config_mode"],
                }

            if tool_msg.name == "get_default_value":
                param = tool_output["parameter_name"]
                default = tool_output["default"]
                pretty = _pretty(param, self.schema_properties)
                reply = (
                    f"The default value for **{pretty}** is `{default}`."
                    if default is not None
                    else f"There is no default defined for **{pretty}**."
                )
                return {
                    "messages": [AIMessage(content=reply)],
                    "config_state": state["config_state"],
                    "in_config_mode": state["in_config_mode"],
                }

            if tool_msg.name == "set_parameter":
                return self._handle_set_parameter(state, tool_output)

            return state

        def should_continue(state: AgentState) -> str:
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools"
            return "end"

        from langgraph.prebuilt import ToolNode

        builder = StateGraph(AgentState)
        builder.add_node("agent", call_model)
        builder.add_node("tools", ToolNode(tools))
        builder.add_node("validator", handle_tool_result)

        builder.set_entry_point("agent")
        builder.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": "__end__"})
        builder.add_edge("tools", "validator")
        builder.add_edge("validator", "__end__")

        return builder.compile()

    # ------------------------------------------------------------ set_parameter

    def _handle_set_parameter(self, state: AgentState, tool_output: dict):
        if not isinstance(tool_output, dict):
            return {
                "messages": [AIMessage(content="Invalid tool output format.")],
                "config_state": state["config_state"],
                "in_config_mode": state["in_config_mode"],
            }

        key = tool_output["parameter_name"]
        raw_value = tool_output["parameter_value"]

        info = self.schema_properties.get(key)
        if not info:
            reply = f"Unknown parameter '{key}'. Please check the name."
            return {
                "messages": [AIMessage(content=reply)],
                "config_state": state["config_state"],
                "in_config_mode": state["in_config_mode"],
            }

        try:
            value = _coerce_type(raw_value, info)

            # Enum check
            if info.get("enum") and isinstance(value, str):
                lc = value.strip().lower()
                match = next((c for c in info["enum"] if str(c).lower() == lc), None)
                if match is None:
                    opts = ", ".join(str(c) for c in info["enum"])
                    return {
                        "messages": [AIMessage(content=f"Invalid value '{value}'. Choose from: {opts}")],
                        "config_state": state["config_state"],
                        "in_config_mode": state["in_config_mode"],
                    }
                value = match

            state["config_state"][key] = value
            self._answered.add(key)

            pretty = _pretty(key, self.schema_properties)
            reply = f"Set **{pretty}** = `{value}`."

        except (ValidationError, ValueError, TypeError) as err:
            reply = f"Invalid value for **{key}**: {err}"

        return {
            "messages": [AIMessage(content=reply)],
            "config_state": state["config_state"],
            "in_config_mode": True,
            "nudge_count": state.get("nudge_count", 0),
        }

    # ------------------------------------------------------------ public API

    def invoke(self, user_text: str, config_state: dict | None = None) -> tuple[str, dict]:
        """Run the agent for a single user turn.

        Returns (reply_text, updated_config_state).
        """
        cfg = dict(config_state or self._config_state)
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_text)],
            "config_state": cfg,
            "in_config_mode": self._in_config_mode,
            "next_to_ask": "",
            "nudge_count": 0,
        }

        result = self.graph.invoke(initial_state)

        self._config_state = result.get("config_state", cfg)
        self._in_config_mode = result.get("in_config_mode", False)

        # Extract the last AI message text
        reply = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                reply = msg.content
                break

        return reply, self._config_state
