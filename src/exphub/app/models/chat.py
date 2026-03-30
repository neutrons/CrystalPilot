"""Pydantic model for the chat pane state."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat bubble."""

    role: str = Field(description="'user' or 'assistant'")
    content: str = Field(default="")


class ChatModel(BaseModel):
    """Observable state for the agent chat pane."""

    messages: List[Dict[str, str]] = Field(
        default_factory=list,
        title="Chat Messages",
        description="List of {role, content} dicts rendered as bubbles.",
    )
    user_input: str = Field(default="", title="User Input")
    is_thinking: bool = Field(default=False, title="Agent Thinking")
    drawer_open: bool = Field(default=False, title="Chat Drawer Open")
    agent_status: str = Field(default="idle", title="Agent Status")
