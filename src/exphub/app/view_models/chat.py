"""ViewModel for the CrystalPilot chat pane.

Manages:
- Lazy agent initialisation
- Submitting user messages to the agent
- Applying agent config changes back into the main model / trame bindings
- Snapshotting the main model state so the agent always has fresh context
- Surfacing bridge validation errors back to the agent on the next turn
"""

from __future__ import annotations

import asyncio
import logging
import threading
from functools import partial
from typing import Any, Dict

from nova.mvvm.interface import BindingInterface

from ...agent.agent import Agent
from ...agent.bridge import BRIDGED_SUBMODELS, apply_agent_config, snapshot_models
from ...agent.schema_gen import enrich_schema_with_options, schema_from_model_instance
from ...agent.utils import pretty_name
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
        nav_fn=None,
    ) -> None:
        self.chat_model = chat_model
        self.main_model = main_model
        self.main_bindings = main_bindings

        self.chat_bind = binding.new_bind(self.chat_model)

        # Agent is created lazily on first message so startup isn't blocked
        self._agent: Agent | None = None
        self._agent_lock = threading.Lock()
        self._nav_fn = nav_fn

        # Bridge errors from the previous turn, forwarded to the next invoke()
        self._pending_bridge_errors: dict[str, str] = {}

    # ------------------------------------------------------------------ agent

    def _ensure_agent(self) -> None:
        """Create the agent on first use (idempotent, thread-safe)."""
        if self._agent is not None:
            return
        with self._agent_lock:
            if self._agent is not None:
                return
            schema_props = schema_from_model_instance(self.main_model)
            for attr in BRIDGED_SUBMODELS:
                sub = getattr(self.main_model, attr, None)
                if sub is not None:
                    schema_props.update(schema_from_model_instance(sub))
            # Enrich schema with live option lists (instrument_list, etc.)
            live_snapshot = snapshot_models(self.main_model)
            schema_props = enrich_schema_with_options(schema_props, live_snapshot)
            # snapshot_fn lets the get_parameter / list_parameters tools read live UI state
            snapshot_fn = partial(snapshot_models, self.main_model)
            self._agent = Agent(schema_properties=schema_props, snapshot_fn=snapshot_fn, nav_fn=self._nav_fn)
            logger.info("CrystalPilot agent initialised with %d schema fields", len(schema_props))

    # ------------------------------------------------------------------ submit

    async def handle_submit(self, user_text: str) -> None:
        """Process a user message: run agent, apply config changes, update UI."""
        if not user_text.strip():
            return

        print(f"[CrystalPilot Agent] User: {user_text[:120]}")
        self.chat_model.messages.append({"role": "user", "content": user_text})
        self.chat_model.user_input = ""
        self.chat_model.is_thinking = True
        self.chat_model.agent_status = "Initialising agent…"
        self._push_chat()

        try:
            self._ensure_agent()
            current_state = snapshot_models(self.main_model)
            pending_errors = self._pending_bridge_errors or None
            self._pending_bridge_errors = {}

            self.chat_model.agent_status = "Calling LLM…"
            self._push_chat()
            print("[CrystalPilot Agent] Calling LLM (run_in_executor)…")

            # Offload the blocking LLM call to a thread-pool executor so the
            # asyncio event loop (and the Trame/Vue UI) stays responsive.
            loop = asyncio.get_running_loop()
            reply, new_config = await loop.run_in_executor(
                None,
                lambda: self._agent.invoke(
                    user_text,
                    config_state=current_state,
                    bridge_errors=pending_errors,
                ),
            )

            print(f"[CrystalPilot Agent] Reply: {reply[:120]}")
            self.chat_model.agent_status = "Applying configuration…"
            self._push_chat()

            changed, errors = apply_agent_config(new_config, self.main_model, self.main_bindings)
            if changed:
                print(f"[CrystalPilot Agent] Updated fields: {changed}")
                logger.info("Agent updated fields: %s", changed)
                schema_props = self._agent.schema_properties
                pretty_fields = [pretty_name(f, schema_props) for f in changed]
                self.chat_model.last_update_summary = "Updated: " + ", ".join(pretty_fields)
                self.chat_model.update_snackbar_visible = True
            if errors:
                logger.warning("Bridge errors (will be surfaced next turn): %s", errors)
                self._pending_bridge_errors = errors

            self.chat_model.messages.append({"role": "assistant", "content": reply})

        except Exception as exc:
            print(f"[CrystalPilot Agent] Error: {exc}")
            logger.exception("Agent error")
            self._pending_bridge_errors = {}
            self.chat_model.messages.append({"role": "assistant", "content": f"Error: {exc}"})

        self.chat_model.is_thinking = False
        self.chat_model.agent_status = ""
        self._push_chat()

    # ------------------------------------------------------------------ helpers

    def toggle_drawer(self) -> None:
        self.chat_model.drawer_open = not self.chat_model.drawer_open
        self._push_chat()

    def _push_chat(self) -> None:
        self.chat_bind.update_in_view(self.chat_model)
