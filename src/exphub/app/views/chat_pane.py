"""Right-side chat panel view for CrystalPilot.

Renders an inline right panel (not an overlay drawer) containing:
- A scrollable message list (user / assistant bubbles)
- A text input bar at the bottom
- A thinking / status indicator
"""

from __future__ import annotations

import asyncio

from trame.widgets import client
from trame.widgets import vuetify3 as vuetify
from trame_client.widgets import html

from ..view_models.chat import ChatViewModel


# ── CSS for chat bubbles (injected via trame client.Style) ─────────────
_CHAT_CSS = """
.chat-bubble {
    max-width: 85%;
    padding: 8px 14px;
    border-radius: 12px;
    margin: 4px 0;
    word-wrap: break-word;
    white-space: pre-wrap;
    font-size: 0.85rem;
    line-height: 1.4;
}
.chat-bubble-user {
    background-color: #1976d2;
    color: white;
    align-self: flex-end;
    margin-left: auto;
    border-bottom-right-radius: 4px;
}
.chat-bubble-assistant {
    background-color: #f5f5f5;
    color: #212121;
    align-self: flex-start;
    margin-right: auto;
    border-bottom-left-radius: 4px;
}
.chat-messages-container {
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    flex: 1 1 auto;
    padding: 12px;
    gap: 4px;
}
.chat-input-area {
    flex: 0 0 auto;
    padding: 8px 12px;
    border-top: 1px solid #e0e0e0;
}
.chat-status-bar {
    flex: 0 0 auto;
    padding: 2px 12px;
    font-size: 0.75rem;
    color: #757575;
    font-style: italic;
    min-height: 20px;
}
"""


class ChatPaneView:
    """Builds the right-side inline chat panel UI."""

    def __init__(self, server, chat_vm: ChatViewModel) -> None:
        self.server = server
        self.chat_vm = chat_vm
        self.ctrl = server.controller

        # Register the submit trigger so the UI can call it from JS.
        # _on_submit is synchronous — it schedules the async handle_submit
        # via asyncio.ensure_future so the trame event loop is not blocked.
        self.ctrl.trigger("chat_submit")(self._on_submit)

        # Connect the chat binding to a trame reactive namespace
        self.chat_vm.chat_bind.connect("chat")

        self.create_ui()

    # ------------------------------------------------------------------ UI

    def create_ui(self) -> None:
        # Inject CSS via trame's client.Style (safe, doesn't use v-html)
        client.Style(_CHAT_CSS)

        # Inline right panel — shown/hidden via v-show so it squeezes the
        # sibling tab-content div rather than overlaying it.
        with html.Div(
            v_show="chat.drawer_open",
            style=(
                "flex: 0 0 400px; display: flex; flex-direction: column; "
                "border-left: 1px solid rgba(0,0,0,0.12); background: white; "
                "overflow: hidden;"
            ),
        ):
            # ── Header ──
            with vuetify.VToolbar(density="compact", color="primary"):
                vuetify.VToolbarTitle("CrystalPilot Agent", style="font-size: 0.95rem;")
                vuetify.VSpacer()
                vuetify.VBtn(
                    icon="mdi-close",
                    variant="text",
                    click=self.chat_vm.toggle_drawer,
                )

            # ── Messages area ──
            with html.Div(classes="chat-messages-container", ref="chatMessages"):
                # :class binds dynamically: 'chat-bubble chat-bubble-user' or 'chat-bubble chat-bubble-assistant'
                with html.Div(
                    v_for="(msg, idx) in chat.messages",
                    key="idx",
                    **{":class": "'chat-bubble chat-bubble-' + msg.role"},
                ):
                    html.Span("{{ msg.content }}")

                # Thinking indicator
                with html.Div(
                    v_show="chat.is_thinking",
                    classes="chat-bubble chat-bubble-assistant",
                    style="font-style: italic; opacity: 0.7;",
                ):
                    html.Span("Thinking ...")

            # ── Status bar (debug / processing step) ──
            with html.Div(classes="chat-status-bar"):
                html.Span("{{ chat.agent_status }}")

            # ── Input area ──
            with html.Div(classes="chat-input-area"):
                vuetify.VTextField(
                    v_model="chat.user_input",
                    placeholder="Ask CrystalPilot Agent…",
                    variant="outlined",
                    density="compact",
                    hide_details=True,
                    append_inner_icon="mdi-send",
                    **{"@keydown.enter": "trigger('chat_submit', [chat.user_input])"},
                    **{"@click:append-inner": "trigger('chat_submit', [chat.user_input])"},
                )

        # Field-update snackbar (shown briefly when the agent writes parameters)
        with vuetify.VSnackbar(
            v_model="chat.update_snackbar_visible",
            timeout=3000,
            color="success",
            location="bottom left",
        ):
            html.Span("{{ chat.last_update_summary }}")

    # ------------------------------------------------------------------ handler

    def _on_submit(self, text: str = "") -> None:
        """Sync trigger handler — schedules the async agent call on the event loop."""
        if not text or not text.strip():
            return
        asyncio.ensure_future(self.chat_vm.handle_submit(text.strip()))
