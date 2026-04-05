"""State types for the LangGraph agent."""

from typing import Any, Dict, List

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State flowing through the LangGraph."""

    messages: List[BaseMessage]
    config_state: Dict[str, Any]
    in_config_mode: bool
    next_to_ask: str
    nudge_count: int
    tool_rounds: int
