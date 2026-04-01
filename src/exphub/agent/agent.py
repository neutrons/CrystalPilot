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
from pathlib import Path
from typing import Any, Literal, Set

from jsonschema import ValidationError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from .llm import get_configured_chat_model
from .rag import BeamlineKnowledgeBase
from .state import AgentState
from .tools import make_tools
from .utils import coerce_type, pretty_name

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).parent / "prompts"


def _load_system_prompt() -> str:
    """Load the system prompt from the external Markdown file."""
    prompt_file = _PROMPT_DIR / "system_prompt.md"
    try:
        return prompt_file.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Could not read %s — using fallback prompt", prompt_file)
        return (
            "You are CrystalPilot Assistant, an AI helper for single-crystal "
            "neutron diffraction experiments at ORNL beamlines. Be concise and helpful."
        )


SYSTEM_PROMPT = _load_system_prompt()


class Agent:
    """CrystalPilot LangGraph agent."""

    def __init__(
        self,
        schema_properties: dict[str, dict],
        snapshot_fn=None,
        nav_fn=None,
        mcp_tools: list | None = None,
    ) -> None:
        self.schema_properties = schema_properties
        self._answered: Set[str] = set()
        self._config_state: dict[str, Any] = {}
        self._in_config_mode = False

        try:
            rag = BeamlineKnowledgeBase()
        except Exception as exc:
            logger.warning("RAG init failed (%s) — retrieve_docs will be unavailable", exc)
            rag = None

        self._tools = make_tools(schema_properties, snapshot_fn=snapshot_fn, nav_fn=nav_fn, rag=rag)
        if mcp_tools:
            self._tools.extend(mcp_tools)
            logger.info("Added %d MCP tools to agent", len(mcp_tools))
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
        builder.add_conditional_edges(
            "validator",
            self._validator_routing,
            {"agent": "agent", "end": "__end__"},
        )
        return builder.compile()

    # ------------------------------------------------------------------ nodes

    def _call_model_node(self, state: AgentState) -> AgentState:
        msgs = [SystemMessage(content=SYSTEM_PROMPT)]

        if state.get("in_config_mode"):
            cfg = state.get("config_state", {})
            msgs.append(SystemMessage(content=f"CONTEXT: Current config values: {json.dumps(cfg, default=str)}"))

        msgs.extend(state["messages"][-6:])

        print("[Agent] Calling LLM…")
        llm = get_configured_chat_model().bind_tools(self._tools)
        out = llm.invoke(msgs)
        tool_calls = getattr(out, "tool_calls", [])
        if tool_calls:
            print(f"[Agent] LLM → tool calls: {[tc['name'] for tc in tool_calls]}")
        else:
            content_preview = (out.content or "")[:80]
            print(f"[Agent] LLM → reply: {content_preview}")
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
        print(f"[Agent] Tool result: {tool_msg.name}")

        try:
            tool_output = json.loads(tool_msg.content)
        except (json.JSONDecodeError, TypeError):
            tool_output = tool_msg.content

        if tool_msg.name == "explain_parameter":
            return self._state_with_reply(state, str(tool_output))

        if tool_msg.name == "get_default_value":
            return self._handle_get_default(state, tool_output)

        if tool_msg.name == "refresh_schema":
            return self._handle_refresh_schema(state, tool_output)

        if tool_msg.name in ("set_multiple_parameters", "apply_preset"):
            return self._handle_set_multiple(state, tool_output)

        if tool_msg.name == "list_presets":
            return self._state_with_reply(state, str(tool_output))

        if tool_msg.name in ("set_parameter", "append_run", "edit_run", "delete_run"):
            if isinstance(tool_output, dict) and "error" in tool_output and "parameter_name" not in tool_output:
                return self._state_with_reply(state, f"Error: {tool_output['error']}")
            return self._handle_set_parameter(state, tool_output)

        if tool_msg.name == "get_parameter":
            return self._handle_get_parameter(state, tool_output)

        if tool_msg.name == "list_parameters":
            return self._handle_list_parameters(state, tool_output)

        if tool_msg.name == "get_angle_plan":
            return self._handle_get_angle_plan(state, tool_output)

        if tool_msg.name == "navigate_to_tab":
            return self._handle_navigate_to_tab(state, tool_output)

        if tool_msg.name == "retrieve_docs":
            # Pass through unchanged — _validator_routing sends back to the
            # agent node so the LLM can synthesise a reply from the passages.
            return state

        return state

    @staticmethod
    def _validator_routing(state: AgentState) -> Literal["agent", "end"]:
        """Route back to the agent after retrieve_docs so it can synthesise a reply."""
        last = state["messages"][-1]
        if isinstance(last, ToolMessage) and last.name == "retrieve_docs":
            return "agent"
        return "end"

    @staticmethod
    def _should_continue(state: AgentState) -> Literal["tools", "end"]:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return "end"

    # ------------------------------------------------------------------ tool handlers

    def _handle_navigate_to_tab(self, state: AgentState, tool_output) -> AgentState:
        if isinstance(tool_output, dict) and "error" in tool_output:
            return self._state_with_reply(state, f"Navigation error: {tool_output['error']}")
        tab = tool_output.get("tab") if isinstance(tool_output, dict) else None
        name = tool_output.get("name", f"tab {tab}") if isinstance(tool_output, dict) else f"tab {tab}"
        return self._state_with_reply(state, f"Switched to **{name}** tab.")

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

    def _handle_refresh_schema(self, state: AgentState, tool_output) -> AgentState:
        if not isinstance(tool_output, dict):
            return self._state_with_reply(state, str(tool_output))
        if "error" in tool_output:
            return self._state_with_reply(state, f"Schema refresh error: {tool_output['error']}")
        fields = tool_output.get("refreshed_fields", [])
        total = tool_output.get("total_fields", 0)
        if fields:
            names = ", ".join(f"**{pretty_name(f, self.schema_properties)}**" for f in fields)
            reply = f"Schema refreshed — updated options for: {names}."
        else:
            reply = f"Schema refreshed — no option changes detected ({total} fields checked)."
        return self._state_with_reply(state, reply)

    def _handle_set_multiple(self, state: AgentState, tool_output: dict) -> AgentState:
        if not isinstance(tool_output, dict):
            return self._state_with_reply(state, "Invalid tool output for multi-set.")
        if "error" in tool_output and "validated" not in tool_output:
            return self._state_with_reply(state, f"Error: {tool_output['error']}")

        validated = tool_output.get("validated", {})
        errors = tool_output.get("errors", {})
        preset_name = tool_output.get("preset_name")

        for key, value in validated.items():
            state["config_state"][key] = value
            self._answered.add(key)

        parts: list[str] = []
        if preset_name:
            parts.append(f"Applied preset **{preset_name}**.")
        if validated:
            fields = ", ".join(
                f"**{pretty_name(k, self.schema_properties)}** = `{v}`"
                for k, v in validated.items()
            )
            parts.append(f"Set {len(validated)} parameter(s): {fields}.")
        if errors:
            errs = ", ".join(f"**{k}**: {v}" for k, v in errors.items())
            parts.append(f"Could not set: {errs}.")

        return {
            "messages": [AIMessage(content=" ".join(parts) or "No changes applied.")],
            "config_state": state["config_state"],
            "in_config_mode": True,
            "nudge_count": state.get("nudge_count", 0),
        }

    def _handle_get_angle_plan(self, state: AgentState, tool_output) -> AgentState:
        if isinstance(tool_output, dict) and "error" in tool_output:
            return self._state_with_reply(state, f"Error reading angle plan: {tool_output['error']}")
        if not isinstance(tool_output, list):
            return self._state_with_reply(state, str(tool_output))
        if not tool_output:
            return self._state_with_reply(state, "The angle plan table is currently empty.")
        header = "| # | Title | phi | omega | Wait For | Value | Or Time |"
        sep    = "|---|-------|-----|-------|----------|-------|---------|"
        rows = [
            f"| {r.get('_index', i)} | {r.get('title', '')} | {r.get('phi', 0)} "
            f"| {r.get('omega', 0)} | {r.get('wait_for', '')} | {r.get('value', 0)} | {r.get('or_time', 0)} |"
            for i, r in enumerate(tool_output)
        ]
        reply = "**Current Angle Plan:**\n\n" + header + "\n" + sep + "\n" + "\n".join(rows)
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
