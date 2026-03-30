"""ViewModel for the CrystalPilot chat pane.

Manages:
- Lazy agent initialisation
- Submitting user messages to the agent
- Applying agent config changes back into the main model / trame bindings
- Snapshotting the main model state so the agent always has fresh context
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict

from nova.mvvm.interface import BindingInterface

from ..models.chat import ChatModel
from ..models.main_model import MainModel

logger = logging.getLogger(__name__)


class ChatViewModel:
    """ViewModel for the right-side agent chat pane."""

    def __init__(
        self,
        chat_model: ChatModel,
        main_model: MainModel,
        binding: BindingInterface,
        main_bindings: Dict[str, Any],
    ) -> None:
        self.chat_model = chat_model
        self.main_model = main_model
        self.main_bindings = main_bindings

        # Trame binding for reactive UI updates
        self.chat_bind = binding.new_bind(self.chat_model)

        # Agent is created lazily on first message so startup isn't blocked
        self._agent = None
        self._agent_lock = threading.Lock()

    # ------------------------------------------------------------------ agent

    def _ensure_agent(self):
        """Create the agent on first use (idempotent, thread-safe)."""
        if self._agent is not None:
            return
        with self._agent_lock:
            if self._agent is not None:
                return
            from ..agent.schema_gen import schema_from_model_instance
            from ..agent.agent import Agent

            schema_props = schema_from_model_instance(self.main_model)

            # Also include sub-model schemas
            for attr in ("experimentinfo", "angleplan", "eiccontrol", "dataanalysis"):
                sub = getattr(self.main_model, attr, None)
                if sub is not None:
                    schema_props.update(schema_from_model_instance(sub))

            self._agent = Agent(schema_properties=schema_props)
            logger.info("CrystalPilot agent initialised with %d schema fields", len(schema_props))

    # ------------------------------------------------------------------ submit

    def handle_submit(self, user_text: str) -> None:
        """Process a user message: run agent, apply config changes, update UI."""
        if not user_text.strip():
            return

        # 1) Append user bubble
        self.chat_model.messages.append({"role": "user", "content": user_text})
        self.chat_model.user_input = ""
        self.chat_model.is_thinking = True
        self._push_chat()

        try:
            self._ensure_agent()

            # 2) Snapshot current UI state so agent has latest values
            from ..agent.bridge import snapshot_models
            current_state = snapshot_models(self.main_model)

            # 3) Run agent
            reply, new_config = self._agent.invoke(user_text, config_state=current_state)

            # 4) Apply any parameter changes back into the models / trame
            from ..agent.bridge import apply_agent_config
            changed = apply_agent_config(new_config, self.main_model, self.main_bindings)
            if changed:
                logger.info("Agent updated fields: %s", changed)

            # 5) Append assistant bubble
            self.chat_model.messages.append({"role": "assistant", "content": reply})

        except Exception as exc:
            logger.exception("Agent error")
            self.chat_model.messages.append(
                {"role": "assistant", "content": f"Error: {exc}"}
            )

        self.chat_model.is_thinking = False
        self._push_chat()

    # ------------------------------------------------------------------ helpers

    def toggle_drawer(self) -> None:
        self.chat_model.drawer_open = not self.chat_model.drawer_open
        self._push_chat()

    def _push_chat(self) -> None:
        """Push the chat model state to the trame view."""
        self.chat_bind.update_in_view(self.chat_model)
