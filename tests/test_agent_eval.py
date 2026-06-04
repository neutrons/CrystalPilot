"""Agent eval harness: golden conversations -> expected tool-calls / writes (C.2).

These run ``Agent.invoke`` end to end through its real LangGraph graph (agent ->
tools -> validator -> loop), but with a *scripted* LLM (the ``scripted_agent_llm``
fixture in tests/conftest.py) so they are deterministic and need no network or
model. They guard the agent's plumbing — tool dispatch, parameter writes,
validation, and the destructive-action gate — against silent regressions from
schema / tool / graph changes. (LLM tool-*selection* quality still needs a real
model; that belongs in an offline eval gated behind an API key, not CI.)
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from exphub.agent.agent import Agent
from exphub.agent.confirmation import ConfirmationGate
from exphub.core.beamline import ActionTool

_SCHEMA = {"max_q": {"title": "Max Q", "type": "number"}}


def ai_tool_call(name: str, args: dict, call_id: str = "call_1") -> AIMessage:
    """An ``AIMessage`` requesting one tool call (LangChain tool-call format)."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


def ai_reply(text: str) -> AIMessage:
    """An ``AIMessage`` that is a final plain-text reply (no tool calls)."""
    return AIMessage(content=text)


def _agent(
    schema: dict | None = None,
    action_tools: tuple[ActionTool, ...] | None = None,
    action_fns: dict | None = None,
    gate: ConfirmationGate | None = None,
) -> Agent:
    return Agent(
        schema_properties=schema or _SCHEMA,
        action_tools=action_tools,
        action_fns=action_fns,
        confirmation_gate=gate,
    )


def test_set_parameter_writes_config(scripted_agent_llm: Any) -> None:
    """User asks to set a value -> set_parameter tool runs -> config reflects it."""
    scripted_agent_llm(
        [
            ai_tool_call("set_parameter", {"parameter_name": "max_q", "parameter_value": 20}),
            ai_reply("Set max_q to 20."),
        ]
    )
    agent = _agent()
    reply, cfg = agent.invoke("set max q to 20", config_state={"max_q": 10})
    assert cfg.get("max_q") in (20, 20.0)
    assert "20" in reply


def test_plain_question_passthrough(scripted_agent_llm: Any) -> None:
    """No tool call -> the LLM's plain reply is returned unchanged."""
    scripted_agent_llm([ai_reply("TOPAZ is a single-crystal diffractometer.")])
    agent = _agent()
    reply, _cfg = agent.invoke("what is topaz?")
    assert "TOPAZ" in reply


def test_destructive_verb_proposes_not_executes(scripted_agent_llm: Any) -> None:
    """Even if the LLM *calls* a destructive verb, the gate blocks execution.

    This is C.1's safety invariant verified end to end through the agent graph:
    a tool call alone can never run a confirmation-required action.
    """
    calls: list[int] = []
    spec = ActionTool(
        name="stop_current_run",
        vm_method="stoprun",
        description="Stop the current run.",
        success_message="Current run stopped.",
        requires_confirmation=True,
    )
    gate = ConfirmationGate()
    scripted_agent_llm(
        [
            ai_tool_call("stop_current_run", {}),
            ai_reply("I've asked for your confirmation before stopping the run."),
        ]
    )
    agent = _agent(action_tools=(spec,), action_fns={"stop_current_run": lambda: calls.append(1)}, gate=gate)
    _reply, _cfg = agent.invoke("stop the run now")
    assert calls == []  # the destructive op did NOT run from the model's call
    assert gate.has_pending()  # it is queued, awaiting an explicit user "yes"


def test_nondestructive_verb_executes_immediately(scripted_agent_llm: Any) -> None:
    """A non-confirmation verb runs the moment the model calls it (current behavior)."""
    calls: list[int] = []
    spec = ActionTool(
        name="authenticate_eic",
        vm_method="call_load_token",
        description="Load the EIC token.",
        success_message="EIC token loaded.",
    )
    scripted_agent_llm([ai_tool_call("authenticate_eic", {}), ai_reply("Authenticated.")])
    agent = _agent(action_tools=(spec,), action_fns={"authenticate_eic": lambda: calls.append(1)})
    _reply, _cfg = agent.invoke("authenticate with EIC")
    assert calls == [1]
