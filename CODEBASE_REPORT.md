# CrystalPilot Codebase Analysis Report

**Date:** 2026-03-30
**Branch:** `agentize`

---

## 1. Project Overview

**CrystalPilot** is a hardware experiment management and data analysis application for single-crystal neutron diffraction experiments at ORNL beamlines (primarily TOPAZ/BL12). It provides researchers with:

- GUI-based hardware configuration and real-time monitoring
- Experiment parameter setup and angle plan management
- 3D Q-space coverage visualization
- EIC (Experiment Information Collection) submission
- AI-powered assistant for guided experiment configuration
- Integration with analysis.sns.gov and Mantid data processing

**Framework:** Built on [Nova-Trame](https://github.com/orgs/nova-trame) (Vue3-based Python GUI framework) with **MVVM architecture**.

---

## 2. Directory Structure

```
CrystalPilot/
├── src/exphub/
│   ├── app/
│   │   ├── __main__.py              # Entry point
│   │   ├── main.py                  # Application bootstrap
│   │   ├── mvvm_factory.py          # ViewModel + binding factory
│   │   ├── models/                  # Pydantic v2 data models
│   │   │   ├── main_model.py        # Root aggregate model
│   │   │   ├── experiment_info.py   # IPTS metadata
│   │   │   ├── angle_plan.py        # Angle/position planning
│   │   │   ├── angle_plan_engine.py # Rotation/coverage computation
│   │   │   ├── eic_control.py       # EIC submission control
│   │   │   ├── eic_client.py        # OAuth + HTTP EIC client
│   │   │   ├── css_status.py        # Control system status
│   │   │   ├── data_analysis.py     # Analysis config + Plotly
│   │   │   ├── temporal_analysis.py # Time-series monitoring
│   │   │   ├── chat.py              # Chat pane state
│   │   │   └── newtabtemplate.py    # Extension template
│   │   ├── view_models/
│   │   │   ├── main.py              # Main ViewModel (~1400 lines)
│   │   │   ├── chat.py              # Chat/Agent ViewModel
│   │   │   └── angle_plan.py        # Angle plan ViewModel
│   │   └── views/
│   │       ├── main_view.py         # Root view / Trame server
│   │       ├── tabs_panel.py        # Tab bar UI
│   │       ├── tab_content_panel.py # Tab content router
│   │       ├── chat_pane.py         # Agent chat drawer
│   │       ├── experiment_info.py   # IPTS Info tab
│   │       ├── angle_plan.py        # Angle Plan tab
│   │       ├── eic_control.py       # EIC Control tab
│   │       ├── css_status.py        # Instrument Status tab
│   │       ├── temporal_analysis.py # Live Data Processing tab
│   │       ├── data_analysis.py     # Data Analysis tab
│   │       └── newtabtemplate.py    # Extension template
│   └── agent/                       # LLM-powered assistant
│       ├── agent.py                 # LangGraph state machine
│       ├── state.py                 # AgentState TypedDict
│       ├── llm.py                   # LLM provider abstraction
│       ├── tools.py                 # LangChain tools
│       ├── schema_gen.py            # Pydantic → JSON schema
│       └── bridge.py                # Agent ↔ UI model sync
├── tests/
├── docs/
├── scripts/
├── xml/                             # EPICS XML configs
├── dockerfiles/
├── pyproject.toml
├── README.md
├── DEVELOPMENT.md
└── CONTRIBUTING.md
```

---

## 3. Application Architecture

CrystalPilot follows the **MVVM (Model-View-ViewModel)** pattern with Nova-Trame's reactive binding system.

```
┌─────────────────────────────────────────────────────────────┐
│  Vue3 Frontend (Trame Components)                           │
│  ┌──────────────┬──────────────┬──────────────────────┐    │
│  │  Tabs Panel  │  Tab Content │  Chat Pane (Drawer)  │    │
│  └──────────────┴──────────────┴──────────────────────┘    │
└───────────────────────┬─────────────────────────────────────┘
                        │  Trame Reactive Bindings
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  ViewModels                                                 │
│  ┌────────────────────────────────────────────────────┐    │
│  │ MainViewModel                                      │    │
│  │  - Orchestrates all sub-ViewModel bindings        │    │
│  │  - Generates Plotly figures                       │    │
│  │  - Handles user action callbacks                  │    │
│  ├────────────────────────────────────────────────────┤    │
│  │ ChatViewModel                                      │    │
│  │  - Lazy-initializes Agent on first message        │    │
│  │  - Submits text → Agent, applies config changes   │    │
│  │  - Manages drawer open/close state                │    │
│  └────────────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────────────┘
                        │  Direct object references
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Models (Pydantic v2)                                       │
│  MainModel                                                  │
│   ├── experimentinfo: ExperimentInfoModel                  │
│   ├── angleplan: AnglePlanModel                            │
│   ├── eiccontrol: EICControlModel                          │
│   ├── cssstatus: CSSStatusModel                            │
│   ├── temporalanalysis: TemporalAnalysisModel              │
│   └── dataanalysis: DataAnalysisModel                      │
│  ChatModel (separate, for agent pane)                      │
└─────────────────────────────────────────────────────────────┘
```

### Reactive Binding Flow

1. User changes a field in the Vue3 UI → Trame state updates
2. `TrameBinding` detects the change → writes to Pydantic model
3. Callback fires in ViewModel (e.g., `update_experimentinfo_options`)
4. ViewModel processes update, recomputes figures if needed
5. Updated data pushed back to Trame state → Vue3 re-renders

---

## 4. Startup Flow

**Entry:** `src/exphub/app/__main__.py` → `main.py`

```
main()
  └─ MainApp.__init__()
       ├── get_server(None, client_type="vue3")       # Trame server
       ├── create_viewmodels(binding)                  # Factory: creates all VMs
       │    ├── MainModel()                            # Root Pydantic model
       │    ├── TrameBinding(server.state)             # Reactive namespace
       │    ├── MainViewModel(model, binding)
       │    └── ChatViewModel(model, binding)
       ├── load_epics_instance()                       # EPICS hardware connection
       └── Build UI hierarchy
            ├── TabsPanel (tab bar)
            ├── TabContentPanel (routed tab views)
            └── ChatPaneView (right-side drawer)
  └─ server.start(**kwargs)
```

---

## 5. Tab Structure

| # | Tab Name | View | Model |
|---|----------|------|-------|
| 1 | IPTS Info | `ExperimentInfoView` | `ExperimentInfoModel` |
| 2 | Live Data Processing | `TemporalAnalysisView` | `TemporalAnalysisModel` |
| 3 | Experiment Steering | `AnglePlanView` | `AnglePlanModel` |
| 4 | Instrument Status | `CSSStatusView` | `CSSStatusModel` |
| 5 | Data Analysis | `DataAnalysisView` | `DataAnalysisModel` |
| — | EIC Control | `EICControlView` | `EICControlModel` |

---

## 6. Core Data Models

### `MainModel` (Root)
Aggregates all sub-models plus `username` / `password` credentials.

### `ExperimentInfoModel`
| Field | Purpose |
|-------|---------|
| `exp_name`, `ipts_number` | Proposal identification |
| `instrument`, `molecular_formula` | Sample info |
| `crystalsystem`, `point_group`, `centering` | Crystal symmetry |
| `UBFileName`, `cal_filename` | UB matrix + calibration |
| `min_dspacing`, `max_dspacing` | Resolution limits |

### `AnglePlanModel`
| Field | Purpose |
|-------|---------|
| `angle_list` | List of motor positions (phi, omega, chi) |
| `angle_list_pd` | `RunPlan` objects (title, comment, wait conditions) |
| `plan_name`, `plan_file`, `plan_type` | Plan metadata |
| `target_coverage` | Experiment coverage target |
| `qpane_cones`, `qpoints_all`, `qpoints_covered` | Q-space visualization data |
| `instrument`, `wavelength`, `UB`, `d_min/max` | Crystal/beam parameters |
| `point_group`, `lattice_centering` | Symmetry for coverage optimization |

Key methods: `load_ap()`, `get_rotation_matrix()`, `get_figure_coverage()`, `convert_plan_format()`

### `EICControlModel`
| Field | Purpose |
|-------|---------|
| `username`, `token`, `token_file` | Authentication |
| `IPTS_number`, `instrument_name`, `beamline` | Experiment metadata |
| `is_simulation` | Test mode flag |
| `eic_submission_*` | Submission status, scan ID list |
| `eic_auto_stop_strategy` | Auto-stopping criteria / thresholds |

Key methods: `submit_eic()`, `stop_run()`

### `DataAnalysisModel`
| Field | Purpose |
|-------|---------|
| `output_dir`, `data_dir` | Data paths |
| `x_axis`, `y_axis`, `z_axis`, `plot_type` | Plot configuration |
| `axis_options`, `plot_type_options` | Available choices |

Key methods: `get_figure()` → Plotly heatmap or scatter

### `ChatModel`
| Field | Purpose |
|-------|---------|
| `messages` | List[Dict] of chat bubbles (role + content) |
| `user_input` | Current user text field |
| `is_thinking`, `drawer_open` | UI state flags |
| `agent_status` | Status indicator string |

---

## 7. Agent Module (LLM-Powered Assistant)

The `agent/` package implements a conversational AI assistant that helps researchers configure experiments through natural language.

### Architecture

```
User text
    │
    ▼
[agent node] ──── LLM with bound tools
    │
    ▼
[tools node] ──── set_parameter | explain_parameter | get_default_value
    │
    ▼
[validator node] ── Validate + coerce types, update config_state
    │
    ▼
Reply text + updated config dict
```

### Key Files

**`agent/agent.py`** — `Agent` class
- `__init__(schema_properties)` — Initialize with flattened Pydantic schema
- `_build_graph()` — Construct LangGraph state machine
- `invoke(user_text, config_state)` → `(reply: str, updated_config: dict)`
- System prompt instructs LLM to guide experiment setup step by step
- Tool validation coerces user values to correct types (arrays, enums, floats)

**`agent/state.py`** — `AgentState` TypedDict
```python
class AgentState(TypedDict):
    messages: List[BaseMessage]      # Conversation history
    config_state: Dict[str, Any]     # Flattened field values
    in_config_mode: bool             # Configuration mode flag
    next_to_ask: str                 # Next field to prompt
    nudge_count: int                 # Interaction counter
```

**`agent/tools.py`** — Three LangChain tools
| Tool | Action |
|------|--------|
| `set_parameter(name, value)` | Record user-provided value |
| `get_default_value(name)` | Return schema default |
| `explain_parameter(name)` | Return field description |

**`agent/llm.py`** — LLM Provider Abstraction
Selects backend via `LLM_PROVIDER` environment variable:
| Value | Backend |
|-------|---------|
| `ollama` / `local` (default) | Local Ollama server |
| `openrouter` | OpenRouter API (OpenAI-compatible) |
| `google` | Google Gemini API |

**`agent/schema_gen.py`**
- `schema_from_pydantic(model_cls)` — Extracts flat `{field: {type, title, description, default, enum}}` map from Pydantic models
- Used by Agent for field validation and explanation

**`agent/bridge.py`** — Bidirectional sync
- `snapshot_models(main_model)` → flat dict of current field values
- `apply_agent_config(config_state, main_model, bindings)` → writes agent changes back to Pydantic models and pushes to Trame view

### Integration Flow (ChatViewModel)

```python
ChatViewModel.handle_submit(user_text)
  ├── bridge.snapshot_models(main_model)        # Capture current state
  ├── agent.invoke(user_text, config_state)      # LLM turn
  ├── bridge.apply_agent_config(...)             # Apply changes to models
  ├── push updated models to Trame view          # Re-render UI
  └── append assistant reply to chat messages
```

---

## 8. Key Classes Summary

| Class | File | Responsibility |
|-------|------|----------------|
| `MainApp` | [views/main_view.py](src/exphub/app/views/main_view.py) | Root view, creates Trame server, builds UI hierarchy |
| `MainViewModel` | [view_models/main.py](src/exphub/app/view_models/main.py) | Orchestrates all bindings, generates figures, sync |
| `ChatViewModel` | [view_models/chat.py](src/exphub/app/view_models/chat.py) | Agent lifecycle, message handling, config apply |
| `MainModel` | [models/main_model.py](src/exphub/app/models/main_model.py) | Root Pydantic aggregate model |
| `Agent` | [agent/agent.py](src/exphub/agent/agent.py) | LangGraph conversational config state machine |
| `EICClient` | [models/eic_client.py](src/exphub/app/models/eic_client.py) | OAuth + REST interface to EIC system |
| `AnglePlanModel` | [models/angle_plan.py](src/exphub/app/models/angle_plan.py) | Angle plan data + rotation/coverage math |
| `TemporalAnalysisModel` | [models/temporal_analysis.py](src/exphub/app/models/temporal_analysis.py) | Time-series live data monitoring |

---

## 9. Dependencies

### Core Framework
| Package | Purpose |
|---------|---------|
| `nova-trame` | Vue3 GUI framework wrapper |
| `nova-epics` | EPICS hardware control |
| `trame-plotly`, `trame-datagrid` | UI widgets |

### Scientific
| Package | Purpose |
|---------|---------|
| `mantid` ≥6.14 | Crystallographic data processing |
| `pandas`, `numpy` | Data handling |
| `plotly` | Interactive visualization |
| `scikit-learn` | ML utilities |

### Agent / LLM
| Package | Purpose |
|---------|---------|
| `langchain` ≥0.3, `langgraph` ≥0.4 | LLM orchestration |
| `langchain-google-genai` | Google Gemini backend |
| `langchain-openai` | OpenRouter/OpenAI backend |
| `langchain-ollama` | Local Ollama backend |
| `python-dotenv` | `.env` credential loading |
| `jsonschema` | Schema validation |

### Authentication
| Package | Purpose |
|---------|---------|
| `cryptography` | Token encryption |
| `python-gitlab` | GitLab integration |
| `requests-oauthlib` | OAuth for EIC client |

---

## 10. Configuration

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, dependencies, ruff/mypy/pytest config |
| `.env` | LLM credentials (`GOOGLE_API_KEY`, `OLLAMA_BASE_URL`, etc.) |
| `xml/BL12_ADnED_2D_4x4.bob` | EPICS control panel XML |
| `.gitlab-ci.yml` | CI/CD pipeline |
| `.pre-commit-config.yaml` | Pre-commit hooks (ruff, mypy) |
| `.pixi/` | Pixi environment cache |

---

## 11. Use Cases

1. **Experiment Configuration** — Fill IPTS proposal info, define crystal symmetry and UB matrix; AI assistant guides through fields via natural language.
2. **Angle Plan Design** — Define motor positions (phi, omega, chi), visualize 3D Q-space coverage, apply crystal symmetry to optimize sampling.
3. **Hardware Monitoring** — Real-time EPICS device status, live data streaming, instrument health metrics.
4. **Data Collection Control** — Submit angle plans to EIC, monitor scan progress, auto-stop on uncertainty/SNR thresholds, abort scans.
5. **Data Export** — Export as CSV/JSON/NPY, send to analysis.sns.gov, create analysis-ready output directories.
6. **Data Analysis** — Interactive Plotly scatter and heatmap visualizations, temporal analysis of live data streams.

---

## 12. Notable Design Decisions

- **Schema-driven Agent** — `schema_gen.py` auto-extracts Pydantic field metadata (type, default, description, enum) to give the LLM accurate knowledge of the config surface without hand-written prompts.
- **Lazy Agent init** — `ChatViewModel` only instantiates the `Agent` on the first user message, avoiding startup overhead.
- **Multi-backend LLM** — A single `llm.py` abstraction supports local (Ollama), cloud (Gemini), and proxy (OpenRouter) backends switchable via env var — no code changes needed.
- **Bridge pattern for Agent↔UI** — `bridge.py` decouples the Agent (pure Python dicts) from the Trame/Pydantic layer, keeping the agent testable in isolation.
- **MVVM with TrameBinding** — Nova-Trame's `TrameBinding` provides two-way sync between Pydantic models and Vue3 reactive state, so ViewModels never manually push every field.
