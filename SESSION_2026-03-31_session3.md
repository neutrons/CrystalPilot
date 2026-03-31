# Dev Session — 2026-03-31 (Session 3)

**Branch:** `agentize`
**Scope:** wslink `ValueError` on Instrument Status tab — root-cause analysis and fix

---

## Background

After switching to the Instrument Status tab and immediately resizing the window,
the following error appeared in the server console:

```
ValueError: memoryview assignment: lvalue and rvalue have different structures
```

The error comes from `wslink/chunking.py`, inside `UnChunker.process_chunk`:

```python
content_view = memoryview(pending_message["content"])
content_view[offset : offset + content_size] = chunk_content   # ← crash here
```

---

## Root-cause analysis

### What triggers it

The TOPAZ beamline has a 1105-wide 2D detector array PV. The nova.epics.trame
JS shim calls `window.trame.state.dirty("epics"); window.trame.state.flush()`
on every EPICS update, sending the entire `epics.pv_data` dict (including
multi-megabyte detector arrays) from browser → Python server.

When the user switches to the Instrument Status tab and immediately resizes the
window, several large state flushes are triggered concurrently. Each flush is
serialised as a msgpack blob and then split into 4 MB chunks by wslink's
`generate_chunks`.

### wslink's default 4 MB limit

`wslink/chunking.py` reads `WSLINK_MAX_MSG_SIZE` at **module import time**:

```python
MAX_MSG_SIZE = int(os.environ.get("WSLINK_MAX_MSG_SIZE", "4194304"))  # 4 MB
```

A 5–8 MB EPICS state flush is split into 2+ chunks, each with the same
randomly-generated 32-bit message ID. If two large messages happen to receive
the same 32-bit ID (collision probability rises with concurrent flushes), or if
a chunk from one message is written into the buffer of another,
`memoryview` raises because `offset + content_size` overshoots the pre-allocated
`bytearray(total_size)`.

### Fix

Raise `WSLINK_MAX_MSG_SIZE` to 32 MB so each EPICS flush fits in a single chunk,
eliminating the multi-chunk reassembly path entirely.

The env var **must be set before wslink is imported** (it is read at module
level, not at call time). The correct place is `main()` in `main.py`, before
the deferred `from .views.main_view import MainApp` import that ultimately pulls
in wslink.

---

## Changes

### `src/exphub/app/main.py` — set env var before wslink import

```python
def main() -> None:
    # Must be set before wslink is imported (it reads MAX_MSG_SIZE at module
    # level).  The TOPAZ 2D detector PV (1105-wide heatmap) produces ~5-8 MB
    # trame state flushes; wslink's default 4 MB chunk limit splits these into
    # 2+ chunks.  Setting the limit above the largest expected message keeps
    # every wslink message as a single chunk, avoiding the partial-message
    # reassembly path that triggers ValueError in chunking.py on the
    # Instrument Status tab.
    os.environ.setdefault("WSLINK_MAX_MSG_SIZE", str(32 * 1024 * 1024))  # 32 MB

    kwargs = {}
    from .views.main_view import MainApp   # ← wslink first imported here
    ...
```

Uses `setdefault` (not forced assignment) to allow explicit user overrides.

### `src/exphub/app/views/main_view.py` — remove dead `setdefault`

A `setdefault("WSLINK_MAX_MSG_SIZE", ...)` call that had been placed in
`create_ui()` was removed. It had no effect because wslink was already imported
by the time `create_ui()` ran.

---

## Uncertainty

The 32-bit ID collision theory is plausible but not confirmed. An alternative
explanation is that two independent concurrent WebSocket messages both produce
partial chunks that land in the same `UnChunker` buffer due to Python's
cooperative multithreading and asyncio task scheduling. Either way, keeping each
message below the chunk limit eliminates the multi-chunk path and should prevent
the error.

**Needs hardware verification** — the fix cannot be tested in a dev environment
without the actual EPICS PVs.

---

## File summary

| File | Change |
|------|--------|
| `src/exphub/app/main.py` | Set `WSLINK_MAX_MSG_SIZE=32MB` before deferred wslink import |
| `src/exphub/app/views/main_view.py` | Removed dead `setdefault` for `WSLINK_MAX_MSG_SIZE` |

---

# Session 4 — Chat pane UX fixes

**Scope:** Non-overlapping agent panel, send button fix, debug print output

---

## Changes

### Inline side panel (no overlay)

The `VNavigationDrawer` was inside `layout.content` → `VMain`, so it could only
overlay the content — it could never push it. Replaced with a plain flex layout:

- `layout.content` now wraps a `display: flex` row
- Left child: `flex: 1 1 0` div holding `TabContentPanel` (shrinks when panel opens)
- Right child: `ChatPaneView` renders an `html.Div` with `v_show="chat.drawer_open"`
  and `flex: 0 0 400px` — shows/hides inline, squeezing the tab content

Toggle button moved from a fixed FAB to the toolbar (`layout.actions`) next to
the exit button.

| File | Change |
|------|--------|
| `app/views/main_view.py` | Added `html` import; flex row in `layout.content`; toolbar toggle button; removed FAB |
| `app/views/chat_pane.py` | Replaced `VNavigationDrawer` with inline `html.Div`; added status bar |

---

### Send button / Enter key fix

`async def _on_submit` registered as a trame controller trigger was not reliably
awaited by trame — pressing Enter or Send did nothing.

**Fix:** Changed `_on_submit` to a synchronous function that calls
`asyncio.ensure_future(self.chat_vm.handle_submit(...))`. This schedules the
coroutine on the running asyncio event loop (which trame owns), guaranteeing
it executes.

| File | Change |
|------|--------|
| `app/views/chat_pane.py` | `_on_submit`: `async def` → `def` + `asyncio.ensure_future` |

---

### Debug print output + status bar

Added `print()` statements throughout the agent pipeline so the terminal shows
what is happening at each step. Also added a status bar in the chat pane that
shows the current processing step during `is_thinking`.

Steps shown:
1. `[CrystalPilot Agent] User: <text>` — when user submits
2. `[CrystalPilot Agent] Calling LLM (run_in_executor)…`
3. `[Agent] Calling LLM…` — inside the LLM node
4. `[Agent] LLM → tool calls: [name, ...]` or `[Agent] LLM → reply: <preview>`
5. `[Agent] Tool result: <tool_name>` — for each tool call
6. `[CrystalPilot Agent] Reply: <preview>`
7. `[CrystalPilot Agent] Updated fields: [...]` — if config changed

Also fixed `asyncio.get_event_loop()` → `asyncio.get_running_loop()` (correct
API when called from inside a running async coroutine in Python 3.10+).

| File | Change |
|------|--------|
| `app/view_models/chat.py` | `print()` at each step; `agent_status` updates; `get_running_loop()` |
| `agent/agent.py` | `print()` in `_call_model_node` and `_handle_tool_result_node` |
| `app/views/chat_pane.py` | Status bar `html.Div` showing `{{ chat.agent_status }}` |

---

## Prompt for next session

```
I'm working on CrystalPilot (neutron diffraction GUI, TOPAZ beamline, ORNL).
Branch: agentize. Stack: Nova-Trame (Vue3 + Python MVVM), Pydantic v2, LangGraph.
Python env: mamba run -n CP-pixi pixi run python

All agent phases (0–7) are complete. Post-phase polish also done:
- Async handle_submit (run_in_executor, no UI freeze)
- Pretty field names in field-change snackbar
- Heading-aware RAG chunking
- 33 unit tests in tests/test_agent.py
- bridge.py Pydantic 2.11 fix (type(sub).model_fields)
- WSLINK_MAX_MSG_SIZE=32MB set in main.py before wslink import (Instrument Status crash fix)
- Inline agent pane (squeezes content, no overlay); send button fixed; debug prints

Read SESSION_2026-03-30.md, SESSION_2026-03-31.md, SESSION_2026-03-31_session2.md,
SESSION_2026-03-31_session3.md (covers sessions 3 and 4) for full history.
No Co-Authored-By in commits.
Next task: [describe here]
```
