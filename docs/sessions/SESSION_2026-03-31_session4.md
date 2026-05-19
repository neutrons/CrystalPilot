# Dev Session — 2026-03-31 (Session 4)

**Branch:** `agentize`
**Scope:** Borrow agent patterns from NeuDiff-Agent into CrystalPilot

---

## Background

CrystalPilot and NeuDiff-Agent are sibling projects for ORNL single-crystal
neutron diffraction, sharing the same stack (LangGraph + Trame + Vue3).
NeuDiff-Agent (at `~/ORNL Dropbox/Zhongcan Xiao/11-agent/code/NeuDiff-Agent`)
has evolved further in areas like RAG quality, workflow management, MCP
integration, and command handling. This session selectively adopted NeuDiff
patterns that fill genuine gaps without disrupting CrystalPilot's clean MVVM
architecture.

---

## Phase A: Prompt & Constants

### A1. Externalize system prompt
- Moved inline 38-line `SYSTEM_PROMPT` string from `agent.py` to
  `src/exphub/agent/prompts/system_prompt.md`
- Adopted NeuDiff's **intent-based 3-job model**:
  - JOB 1 (Q&A): use `retrieve_docs` first for knowledge questions
  - JOB 2 (Configuration): IMMEDIATELY call `set_parameter` when user gives
    a value — no text chatter (the "Configuration Grammar" rule)
  - JOB 3 (Navigation/General): tab switching, greetings, unclear intent
- `agent.py` now loads the prompt via `Path.read_text()` with a fallback

### A2. Extract constants
- Created `src/exphub/agent/constants.py`
- Moved `EXPERIMENT_PRESETS`, `TAB_MAP`, `TAB_NAMES` out of `tools.py`
- `tools.py` now imports from `constants`

### A3. Enrich knowledge base
- Added 4 **Parameter Reference** tables to `beamline_guide.md`:
  - Sample Information (9 fields)
  - Reduction Input (10 fields)
  - Peak Input (13 fields)
  - Anvred Input (11 fields)
- Field descriptions borrowed from NeuDiff's `assets/schema/schema.json`

---

## Phase B: Command Handler Pipeline

### B1. Pre-agent handler chain
- Created `src/exphub/agent/handlers.py` with 4 deterministic handlers:
  - `handle_help` — "help" / "what can you do"
  - `handle_show_config` — "show config" / "current settings"
  - `handle_list_presets` — "list presets" / "what presets"
  - `handle_navigate` — "go to [tab]" / "switch to [tab]"
- Handlers return a reply string to short-circuit, or `None` to fall through
- Wired into `ChatViewModel.handle_submit()` — runs before `agent.invoke()`,
  skipping the LLM call entirely for matched commands
- Pattern adapted from NeuDiff's `command_handlers.py` but simplified to a
  single flat module (CrystalPilot has fewer special commands)

---

## Phase C: RAG Upgrade

### C1. ChromaDB + SentenceTransformer
- Rewrote `src/exphub/agent/rag.py`:
  - Primary: ChromaDB `PersistentClient` with `SentenceTransformer("all-MiniLM-L6-v2")`
  - Fallback: TF-IDF (scikit-learn) if ChromaDB not installed
  - Lazy model loading via `_LazyEmbeddingFunction` class variable
  - Content-hash-based auto-rebuild (detects when `.md` files change)
  - Persistent vector store at `knowledge/chroma_db/`
- Kept CrystalPilot's heading-aware chunking (splits on `## `, 150-word
  windows with 25-word overlap) — superior to NeuDiff's approach
- Same public API: `BeamlineKnowledgeBase.__init__`, `.retrieve(query, k)`,
  `.document_count`

### C2. Web crawler utility
- Created `scripts/crawl_ornl_docs.py` — offline utility to crawl ORNL
  beamline pages and save as `.md` files in `knowledge/crawled/`
- Crawls 4 root URLs (single-crystal.ornl.gov, neutrons.ornl.gov/{topaz,
  corelli, mandi}) one level deep
- Adapted from NeuDiff's `web_crawler.py`

---

## Phase D: MCP Integration

### D1. MCP service
- Created `src/exphub/agent/mcp_service.py` — generic MCP client adapted
  from NeuDiff's `services/mcp_service.py`
- `MCPServerConfig` (Pydantic): name, command, args, env, enabled
- `MCPService`: async stdio connections, MCP→LangChain tool conversion,
  5s/10s timeouts, graceful degradation
- Wired into:
  - `Agent.__init__()` — accepts optional `mcp_tools` list, appends to
    base tools
  - `ChatViewModel._ensure_agent()` — collects MCP tools before agent init
- Config loaded from JSON file via `load_configs_from_file()`

---

## Phase E: Workflow Phases (Deferred)

Not implemented — CrystalPilot's scope is experiment configuration, not
post-experiment processing. NeuDiff's `PhaseManager` is noted as a reference
for when CrystalPilot adds reduction/refinement pipelines.

---

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `src/exphub/agent/agent.py` | Modified | Load prompt from file, accept MCP tools |
| `src/exphub/agent/tools.py` | Modified | Import constants from `constants.py` |
| `src/exphub/agent/rag.py` | Rewritten | ChromaDB + SentenceTransformer with TF-IDF fallback |
| `src/exphub/agent/knowledge/beamline_guide.md` | Modified | Added 4 parameter reference tables |
| `src/exphub/app/view_models/chat.py` | Modified | Handler chain + MCP service integration |
| `src/exphub/agent/prompts/system_prompt.md` | **New** | Externalized intent-based system prompt |
| `src/exphub/agent/constants.py` | **New** | Presets, tab maps |
| `src/exphub/agent/handlers.py` | **New** | Pre-agent command handler pipeline |
| `src/exphub/agent/mcp_service.py` | **New** | MCP server integration service |
| `scripts/crawl_ornl_docs.py` | **New** | Offline web crawler for ORNL docs |

## Tests

All 33 existing tests pass (`mamba run -n CP-pixi pixi run python -m pytest tests/test_agent.py`).
