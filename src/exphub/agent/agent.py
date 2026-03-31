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
from typing import Any, Literal, Set

from jsonschema import ValidationError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from .llm import get_configured_chat_model
from .state import AgentState
from .tools import make_tools
from .utils import coerce_type, pretty_name

logger = logging.getLogger(__name__)

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


class Agent:
    """CrystalPilot LangGraph agent."""

    def __init__(self, schema_properties: dict[str, dict], snapshot_fn=None) -> None:
        self.schema_properties = schema_properties
        self._answered: Set[str] = set()
        self._config_state: dict[str, Any] = {}
        self._in_config_mode = False
        self._tools = make_tools(schema_properties, snapshot_fn=snapshot_fn)
        self.graph = self._build_graph()

    # ------------------------------------------------------------------ graph

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("agent", self._call_model_node)
        builder.add_node("tools", ToolNode(self._tools))
        builder.add_node("validator", self._handle_tool_result_node)

        builder.set_entry_point("agent")
        builder.add_conditional_edges(
            "agent",
            self._should_continue,
            {"tools": "tools", "end": "__end__"},
        )
        builder.add_edge("tools", "validator")
        builder.add_edge("validator", "__end__")
        return builder.compile()

    # ------------------------------------------------------------------ nodes

    def _call_model_node(self, state: AgentState) -> AgentState:
        msgs = [SystemMessage(content=SYSTEM_PROMPT)]

        if state.get("in_config_mode"):
            cfg = state.get("config_state", {})
            msgs.append(SystemMessage(content=f"CONTEXT: Current config values: {json.dumps(cfg, default=str)}"))

        msgs.extend(state["messages"][-6:])

        llm = get_configured_chat_model().bind_tools(self._tools)
        out = llm.invoke(msgs)
        return {
            "messages": [out],
            "config_state": state.get("config_state", {}),
            "in_config_mode": state.get("in_config_mode", False),
            "nudge_count": state.get("nudge_count", 0),
        }

    def _handle_tool_result_node(self, state: AgentState) -> AgentState:
        tool_msg = state["messages"][-1]
        if not isinstance(tool_msg, ToolMessage):
            return state

        try:
            tool_output = json.loads(tool_msg.content)
        except (json.JSONDecodeError, TypeError):
            tool_output = tool_msg.content

        if tool_msg.name == "explain_parameter":
            return self._state_with_reply(state, str(tool_output))

        if tool_msg.name == "get_default_value":
            return self._handle_get_default(state, tool_output)

        if tool_msg.name == "set_parameter":
            return self._handle_set_parameter(state, tool_output)

        if tool_msg.name == "get_parameter":
            return self._handle_get_parameter(state, tool_output)

        if tool_msg.name == "list_parameters":
            return self._handle_list_parameters(state, tool_output)

        return state

    @staticmethod
    def _should_continue(state: AgentState) -> Literal["tools", "end"]:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return "end"

    # ------------------------------------------------------------------ tool handlers

    def _handle_get_parameter(self, state: AgentState, tool_output: dict) -> AgentState:
        if not isinstance(tool_output, dict):
            return self._state_with_reply(state, "Could not read parameter value.")
        param = tool_output.get("parameter_name", "?")
        err = tool_output.get("error")
        if err:
            return self._state_with_reply(state, f"Could not read **{param}**: {err}")
        value = tool_output.get("value")
        label = pretty_name(param, self.schema_properties)
        reply = f"Current value of **{label}** is `{value}`." if value is not None else f"**{label}** is not set."
        opts = tool_output.get("valid_options")
        if opts:
            reply += " Valid options: " + ", ".join(f"`{o}`" for o in opts) + "."
        return self._state_with_reply(state, reply)

    def _handle_list_parameters(self, state: AgentState, tool_output) -> AgentState:
        if isinstance(tool_output, list):
            lines = [f"- **{p['title']}** (`{p['name']}`)" +
                     (f": {p['description']}" if p.get("description") else "") +
                     (f" — options: {', '.join(p['options'])}" if p.get("options") else "")
                     for p in tool_output]
            reply = "**Available parameters:**\n" + "\n".join(lines)
        else:
            reply = str(tool_output)
        return self._state_with_reply(state, reply)

    def _handle_get_default(self, state: AgentState, tool_output: dict) -> AgentState:
        param = tool_output["parameter_name"]
        default = tool_output["default"]
        label = pretty_name(param, self.schema_properties)
        if default is not None:
            reply = f"The default value for **{label}** is `{default}`."
        else:
            reply = f"There is no default defined for **{label}**."
        return self._state_with_reply(state, reply)

    def _handle_set_parameter(self, state: AgentState, tool_output: dict) -> AgentState:
        if not isinstance(tool_output, dict):
            return self._state_with_reply(state, "Invalid tool output format.")

        key = tool_output["parameter_name"]
        raw_value = tool_output["parameter_value"]

        info = self.schema_properties.get(key)
        if not info:
            return self._state_with_reply(state, f"Unknown parameter '{key}'. Please check the name.")

        try:
            value = coerce_type(raw_value, info)

            if info.get("enum") and isinstance(value, str):
                lc = value.strip().lower()
                match = next((c for c in info["enum"] if str(c).lower() == lc), None)
                if match is None:
                    opts = ", ".join(str(c) for c in info["enum"])
                    return self._state_with_reply(state, f"Invalid value '{value}'. Choose from: {opts}")
                value = match

            state["config_state"][key] = value
            self._answered.add(key)
            label = pretty_name(key, self.schema_properties)
            reply = f"Set **{label}** = `{value}`."

        except (ValidationError, ValueError, TypeError) as err:
            reply = f"Invalid value for **{key}**: {err}"

        return {
            "messages": [AIMessage(content=reply)],
            "config_state": state["config_state"],
            "in_config_mode": True,
            "nudge_count": state.get("nudge_count", 0),
        }

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _state_with_reply(state: AgentState, reply: str) -> AgentState:
        return {
            "messages": [AIMessage(content=reply)],
            "config_state": state["config_state"],
            "in_config_mode": state["in_config_mode"],
        }

    # ------------------------------------------------------------------ public API

    def invoke(
        self,
        user_text: str,
        config_state: dict | None = None,
        bridge_errors: dict[str, str] | None = None,
    ) -> tuple[str, dict]:
        """Run the agent for a single user turn.

        Parameters
        ----------
        user_text:
            The latest message from the user.
        config_state:
            Current flat config snapshot from the UI (bridge.snapshot_models).
        bridge_errors:
            Optional dict of ``{field: error_msg}`` from the *previous* turn's
            ``apply_agent_config`` call. When provided, these are prepended as a
            system note so the agent knows which writes failed and why.

        Returns
        -------
        (reply_text, updated_config_state)
        """
        cfg = dict(config_state or self._config_state)

        messages: list = []
        if bridge_errors:
            lines = "\n".join(f"- `{k}`: {v}" for k, v in bridge_errors.items())
            messages.append(HumanMessage(
                content=f"[SYSTEM] The following parameter writes were rejected by the UI:\n{lines}\n"
                        "Please inform the user and suggest corrections."
            ))
        messages.append(HumanMessage(content=user_text))

        initial_state: AgentState = {
            "messages": messages,
            "config_state": cfg,
            "in_config_mode": self._in_config_mode,
            "next_to_ask": "",
            "nudge_count": 0,
        }

        result = self.graph.invoke(initial_state)

        self._config_state = result.get("config_state", cfg)
        self._in_config_mode = result.get("in_config_mode", False)

        reply = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                reply = msg.content
                break

        return reply, self._config_state
