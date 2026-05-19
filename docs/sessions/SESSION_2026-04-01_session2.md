# Session 2026-04-01 (Session 2): Agent Expert Knowledge from NeuDiff-Agent

## Objective

Analyze CrystalPilot and NeuDiff-Agent codebases in depth, compare their
agent architectures, and port the highest-impact improvements from
NeuDiff-Agent into CrystalPilot's agent system — focusing on expert
knowledge, scientific validation, and workflow orchestration.

## Codebase Comparison (Key Findings)

Both projects serve complementary stages of neutron diffraction:
- **CrystalPilot**: experiment control (during) — Vue 3 SPA via Trame,
  EPICS/SPICE integration, live data streaming, angle plan management
- **NeuDiff-Agent**: data analysis (after) — Trame UI, SSH remote execution,
  SHELX refinement, CheckCIF validation

Both share the same LangGraph agent architecture (CrystalPilot borrowed the
pattern from NeuDiff-Agent). The key gaps identified in CrystalPilot's agent:

| Gap | NeuDiff-Agent | CrystalPilot (before) |
|-----|---------------|----------------------|
| Scientific validation | Crystal cascade maps, unit cell check | Pydantic type checking only |
| RAG quality | 60-candidate reranking, synthesis LLM | Top-3 raw passages, 2 LLM calls |
| Knowledge base | Web-crawled 7 URLs + rich schema | Single 360-line guide |
| Workflow engine | PhaseManager state machine | Prompt-only guidance |
| Handler pipeline | PRE/POST handlers, intent detection | 4 simple handlers |
| Schema scoping | Per-phase field filtering | All fields always visible |

## Changes Implemented

### Tier 1: Scientific Validation (commits `2fe9c1b`, `95d5906`)

**1A — Crystal system cascade** (`src/exphub/agent/validation.py`, new file):
- `CRYSTAL_SYSTEM_POINT_GROUP_MAP` — 8 crystal systems -> valid point groups
- `POINT_GROUP_CENTERING_MAP` — 30+ point groups -> valid centering types
- `validate_point_group()` and `validate_centering()` — reject invalid combos
- `dependent_fields_to_reset()` — clear downstream fields on upstream change
- Integrated into `agent.py:_handle_set_parameter`

**1B — Unit cell volume sanity check** (`validation.py`):
- `_count_atoms()` — parse molecular formula (e.g. "C6H12O6" -> 24)
- `check_unit_cell_volume()` — flags volumes below atoms x Z x 10 A^3
- Triggered when `molecular_formula`, `Z`, or `unit_cell_volume` changes

**2C — Knowledge base expansion** (`beamline_guide.md`, 360 -> 684 lines):
- DEMAND and IMAGINE instrument descriptions + 5-instrument comparison table
- Crystal system -> point group -> centering cascade reference inline
- Unit cell volume sanity check guidance
- Satellite peak configuration section (11 parameters documented)
- Anvred correction parameters with detailed explanations (z_score, etc.)
- Angle plan optimization guidelines
- Live data processing workflow and monitoring checklist
- Expanded troubleshooting (6 scenarios, up from 4)
- Updated parameter reference tables to match actual Pydantic model field names

### Tier 2: Enhanced RAG (commit `39adf88`)

**2A — Keyword-boosted reranking** (`src/exphub/agent/rag.py`):
- `_keyword_score()` — BM25-ish overlap scorer with stop word filtering
- `_retrieve_chromadb()` now fetches 60 candidates and reranks by keyword overlap
- `retrieve_with_budget()` — accumulates reranked passages to 3000-token limit
- `_estimate_tokens()` — rough token count (words x 1.3)

**2B — Direct RAG synthesis** (`rag.py` + `agent.py`):
- `kb.answer(query)` — retrieves with budget, calls LLM with "answer from CONTEXT only"
- `_handle_retrieve_docs()` in agent synthesizes directly in validator node
- Removed two-hop routing (validator -> agent -> end); now validator -> end
- Saves one LLM round-trip per knowledge question

### Tier 3 + 4: Workflow & Handlers (commit `6b41a0c`)

**3A — PhaseManager** (`src/exphub/agent/workflow.py`, new file):
- 7-phase state machine: setup -> monitor -> plan -> refine_plan -> submit -> observe -> analyse
- Per-phase field definitions (`field_prefixes`) for schema scoping
- `PhaseState` tracking (pending/active/complete) with confirmation gates
- `complete_current()`, `advance()`, `go_to_phase()` transitions
- `status_summary()` for markdown workflow overview

**3B — Phase-scoped schema** (`agent.py:_call_model_node`):
- When PhaseManager is available, injects "CURRENT PHASE" context into system message
- Scopes parameter list to fields relevant to the active phase
- Falls back to full parameter list when no PhaseManager or phase has no field_prefixes

**4A — Intent detection** (`handlers.py:handle_intent`):
- Detects workflow-starting phrases ("start experiment", "data analysis", etc.)
- Maps phase-specific keywords to the correct phase
- Auto-navigates to the corresponding tab

**4B — Phase confirmation + status** (`handlers.py`):
- `handle_phase_confirm()` — intercepts "yes"/"no" when phase transition pending
- `handle_workflow_status()` — responds to "where am I" / "show status"
- Both bypass LLM for instant response

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `src/exphub/agent/validation.py` | Created | 120 |
| `src/exphub/agent/workflow.py` | Created | 195 |
| `src/exphub/agent/agent.py` | Modified | +70 / -15 |
| `src/exphub/agent/rag.py` | Modified | +130 / -15 |
| `src/exphub/agent/handlers.py` | Modified | +130 / -5 |
| `src/exphub/agent/knowledge/beamline_guide.md` | Rewritten | 360 -> 684 |
| `src/exphub/app/view_models/chat.py` | Modified | +6 |
| `tests/test_agent.py` | Modified | +245 |

## Test Results

All tests passing: **72 tests** (up from 33 at start of session).

New test classes added:
- `TestValidatePointGroup` (3 tests)
- `TestValidateCentering` (3 tests)
- `TestDependentFieldsToReset` (3 tests)
- `TestCheckUnitCellVolume` (5 tests)
- `TestKeywordScore` (4 tests)
- `TestBeamlineKnowledgeBase` (3 new tests for reranking/budget)
- `TestPhaseManager` (9 tests)
- `TestHandleIntent` (4 tests)
- `TestHandlePhaseConfirm` (3 tests)
- `TestHandleWorkflowStatus` (2 tests)

## Commits

| Hash | Message |
|------|---------|
| `2fe9c1b` | Agent: add crystallographic cross-field validation |
| `95d5906` | Agent: expand knowledge base from 360 to 684 lines |
| `39adf88` | Agent: keyword-boosted RAG reranking and direct synthesis |
| `6b41a0c` | Agent: add PhaseManager, intent detection, and phase-scoped schema |

## Architecture After Changes

```
src/exphub/agent/
├── agent.py           # LangGraph graph, tool validators, phase-aware LLM calls
├── bridge.py          # Bidirectional config sync (Agent <-> UI)
├── constants.py       # Presets, tab mappings
├── handlers.py        # Pre-agent handlers: help, config, presets, navigate,
│                      #   intent detection, phase confirmation, workflow status
├── knowledge/
│   └── beamline_guide.md  # 684-line knowledge base (5 instruments, satellite
│                          #   peaks, Anvred, troubleshooting, parameter refs)
├── llm.py             # LLM provider abstraction (Gemini/OpenRouter/Ollama)
├── mcp_service.py     # Model Context Protocol integration
├── prompts/
│   └── system_prompt.md   # System prompt with 7-phase workflow guidance
├── rag.py             # ChromaDB + keyword reranking + synthesis LLM
├── schema_gen.py      # Pydantic -> flat schema auto-generation
├── state.py           # AgentState TypedDict
├── tools.py           # 15 LangChain tools (set/get/explain params, angle
│                      #   plan, presets, schema refresh, RAG retrieval)
├── utils.py           # coerce_type, pretty_name
├── validation.py      # Crystal cascade maps, unit cell volume check  [NEW]
└── workflow.py        # PhaseManager 7-phase state machine              [NEW]
```
