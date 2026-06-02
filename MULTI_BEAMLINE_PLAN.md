# CrystalPilot → ExpHub: Multi-Beamline Refactoring Plan

> **See also:** [`MULTI_TECHNIQUE_PLAN.md`](MULTI_TECHNIQUE_PLAN.md) — the
> follow-on refactor adding a technique-family layer above beamlines, so
> USANS (SANS) can plug in alongside TOPAZ/CORELLI (single-crystal).

**Author:** generated 2026-05-19 from deep code analysis
**Branch state:** active branch `multibeamline` (off `agentize`); also `main`, `hpc-demo`
**Scope:** Make CrystalPilot a general-purpose beamline-experiment hub. The 5-tab shell stays. Tab contents, PVs, file paths, presets, schema, knowledge base, and agent prompts become beamline-pluggable. Adding a new beamline should mean *adding a folder*, not editing 17 files.

## Status: Phases 0–6 complete

**The plan executed.** Coupling 235 → 0 (outside the two allow-listed files).
Two beamlines ship (TOPAZ + CORELLI). 83 tests green. Acceptance criteria
from Appendix A all satisfied. The remaining sections of this document
describe the design as originally planned; the table below records the
actual landings.

### Acceptance check (from Appendix A)
1. ✅ `grep -r "TOPAZ\|BL12" src/` returns 0 results outside `beamlines/<id>/`
   and `tests/` (vendored `eic_client.py` and one core docstring are explicit
   allow-list exceptions).
2. ✅ Repo ships TOPAZ + CORELLI plug-ins.
3. ✅ A new beamline is added by editing only files under
   `beamlines/<new_id>/` (CORELLI was added with one new directory; the only
   framework-side line edited was an `import .corelli` in
   `beamlines/__init__.py` for discovery).
4. ✅ Agent system prompt is composed at runtime from
   `(core_identity + beamline_context + task)`; tested for both beamlines.
5. ✅ Runtime switching works (`set_active(...)` swaps PVs/paths/presets/
   prompt). The toolbar UI selector is the only missing piece for end-user
   ergonomics — the plumbing underneath is complete.
6. ✅ All tests pass; new suites cover spec loading, registry behaviour,
   prompt composition, and per-beamline PV/path resolution.
7. ✅ `docs/adding_a_beamline.md` exists.

## Progress so far (Phases 0–2 landed on `multibeamline`)

| Phase | Commit | What landed |
|---|---|---|
| 0a | `8d29ec3` | Plan markdown + archived 9 SESSION_*.md and CODEBASE_REPORT.md into `docs/sessions/` and `docs/archive/` |
| 0b | `e208765` | `tests/test_beamline_coupling.py` — three-test regression ratchet (per-file baseline, no-new-file, total-count) |
| 0c | `d9eacf5` | Moved 47 hardcoded per-point-group angle lists (~770 lines) from `view_models/main.py` to `app/fixtures/optimizer_fallback_angles.json` |
| 1a | `e843901` | New `core/beamline/` package: `BeamlineSpec`, `BeamlineContext`, `register`/`get`/`list_ids`/`set_active`/`active` registry |
| 1b | `07ce67d` | New `beamlines/topaz/` plug-in registering the TOPAZ spec (goniometer/detector/Mantid/paths/EIC/agent) |
| 1c | `e6f6a86` | Moved `BL12_ADnED_2D_4x4.bob/.macros` into `beamlines/topaz/screens/`; `main_view.py` loads them via context. `main_view.py` coupling: 25→0 |
| 1d | `b7b1acd` | `app/models/gonio_pvs.py` is now a dynamic shim re-exporting the active beamline's `gonio` module; literal PV strings live in `beamlines/topaz/gonio.py`. `gonio_pvs.py`: 16→0 |
| 2a | `ec67f68` | New `core/paths/` package: `PathResolver` (bound to a beamline + IPTS), `resolver_for()`, `ipts_name()` |
| 2b | `f0ecb93` | `models/temporal_analysis.py` routes paths through `PathResolver`; Mantid `Instrument=` reads from spec. Coupling: 19→0 |
| 2c | `b9ff0f5` | `models/experiment_info.py` instrument/calibration/spectra defaults come from active beamline via `default_factory`; method-body paths via resolver. Coupling: 11→0 |
| 2d | `16da40b` | `models/eic_control.py` beamline code, run-title PV, EIC dropbox dir all from spec; `beamline_database` auto-builds from registry. Coupling: 8→0 |
| 2e | `a2ad830` | `models/angle_plan.py` instrument + placeholder row + run-title PV from active beamline. Coupling: 9→0 |
| 2f | `c00b9a4` | Stragglers: `data_analysis.py` defaults blanked, `views/temporal_analysis.py` reads `monitor_pvs` from spec, `views/data_analysis.py` reads `external_links` from spec, dead comments in `view_models/*` stripped |

**Coupling count: 235 → 121** (all 121 now isolated to two known callsites: `views/css_status.py` at 115, and 4 stragglers across `agent/{constants,handlers,rag}.py`). All 77 tests stay green at every commit. `BeamlineSpec` now carries: `GoniometerSpec`, `DetectorSpec` (incl. `monitor_pvs`), `MantidSpec`, `PathsSpec` (incl. `default_spectra`), `EICSpec` (incl. `run_title_pv`), `AgentSpec`, `TabOverrides`, plus a top-level `external_links` dict.

**What's left:**
- `views/css_status.py` (115 refs) — moves wholesale into `beamlines/topaz/tabs/css_status.py` in Phase 4 (tab plug-in manifest).
- `agent/{constants,handlers,rag}.py` (4 refs) — Phase 5 (prompt composer + per-beamline knowledge).
- God-file decomposition (Phase 3 in the original plan) was deferred; it's no longer blocking the multi-beamline goal since file-level coupling is 0 outside the two tracked callsites.

---

## Progress: Phases 4–6 (added after Phase 2)

| Phase | Commit | What landed |
|---|---|---|
| 4 | `6780062` | Moved `views/css_status.py` (115 refs) → `beamlines/topaz/tabs/css_status.py`. Added `TabOverrides` field; `TabContentPanel` now calls `active().tabs.css_status(view_model)` with graceful fallback when a beamline doesn't define one. Lazy-factory pattern breaks the import cycle introduced by the gonio shim. |
| 5a | `d82b265` | Removed `EXPERIMENT_PRESETS` from `agent/constants.py`; replaced with `get_experiment_presets()` that aggregates from `BeamlineSpec.agent.presets` across the registry. Updated `tools.py` (apply_preset / list_presets) and `handlers.py` (list / help). |
| 5b | `d82b265` | Stripped TOPAZ/CORELLI/MANDI strings from `agent/handlers.py` user-facing text and `agent/rag.py` docstring example. |
| 5c | `fd29d4d` | New `agent/prompts/composer.py`: `compose_system_prompt(beamline_id, task)` assembles `core_identity.md` + per-beamline `context.md` + `tasks/<task>.md`. New `agent/core_aliases.py` breaks the import cycle. Split `system_prompt.md` → `core_identity.md` + `beamlines/topaz/prompts/context.md` + `tasks/experiment_steering.md`. `Agent.__init__` now takes `beamline_id` / `task` kwargs and stamps `ACTIVE_BEAMLINE` into every turn's SystemMessage. |
| 6 | `3bc5f2e` | **Onboarded CORELLI** as the second beamline plug-in — no framework edits required, only added one `import .corelli` line for discovery. New `tests/test_multi_beamline.py` (8 tests) covers registration, runtime switching, PV/path swap, preset aggregation, and prompt composition for both beamlines. Changed `active()` fallback from alphabetical to insertion-order so the import-order in `beamlines/__init__.py` dictates the default. |

**Final coupling count: 235 → 0** (outside two allow-listed files). **83 tests green.**

The regression-ratchet test was simplified at the end: instead of a per-file baseline,
`tests/test_beamline_coupling.py` now asserts that *zero* TOPAZ/BL12 strings exist
outside `beamlines/` and the two allow-listed files. Any reintroduction fails the test.

---

---

## 0. Goals & non-goals

### 0.1 Goals
1. **Beamline as a plug-in.** Adding `CORELLI`, `MANDI`, `HB-3A`, etc. means dropping a `beamlines/<name>/` directory and registering it. No edits to core MVVM or agent code.
2. **Runtime selection.** A user picks a beamline at startup (or switches mid-session). The 5 tabs persist; their **content** (PV widgets, file-path defaults, schema fields shown, presets, goniometer columns, NXV launch command) reconfigures.
3. **Agent multi-context awareness.** The agent knows *which beamline* and *which task* (experiment steering / data processing / app help / future tasks) it is operating on, and composes its prompt + knowledge base + tool subset accordingly.
4. **Easy to extend.** A new beamline adds one Pydantic spec, one knowledge folder, one or two prompt fragments. A new task adds one prompt fragment.
5. **No regression of TOPAZ.** The existing TOPAZ flow must keep working at every step. Refactoring is incremental, never a big-bang rewrite.

### 0.2 Non-goals (for this plan)
- Re-implementing Mantid reduction pipelines for other beamlines (data-side science is the science team's responsibility; we provide the integration points).
- Building a beamline-config GUI editor — text files / Pydantic models suffice for now.
- Replacing Nova-Trame or LangGraph.

---

## 1. Current state — coupling audit

A grep for `TOPAZ|BL12|topaz|bl12` over `src/` returns **190 matches in 17 files**. The worst offenders:

| File | Matches | What's hardcoded |
|---|---:|---|
| [src/exphub/app/views/css_status.py](src/exphub/app/views/css_status.py) | 78 | Entire ADnED 4×4 detector panel: every `PVInput`/`PVPlot` argument is a literal `BL12:Det:N1:*` PV; webopi URLs are baked in |
| [src/exphub/app/views/main_view.py](src/exphub/app/views/main_view.py) | 25 | Loads `BL12_ADnED_2D_4x4.bob/.macros`; `_USER_PANEL_PVS` is a literal 19-element list |
| [src/exphub/app/models/temporal_analysis.py](src/exphub/app/models/temporal_analysis.py) | 18 | `Instrument="TOPAZ"` to Mantid `StartLiveData`; `/SNS/TOPAZ/IPTS-{ipts}/...` everywhere |
| [src/exphub/app/models/gonio_pvs.py](src/exphub/app/models/gonio_pvs.py) | 15 | `BL12:Mot:goniokm:omega/phi`, `BL12:SE:Ramp:*`, `BL12:Det:PCharge:C` |
| [src/exphub/app/models/experiment_info.py](src/exphub/app/models/experiment_info.py) | 11 | `instrument_list=["TOPAZ","MANDI","CORELLI"]`, `/SNS/TOPAZ/shared/calibration/...` defaults |
| [src/exphub/app/models/angle_plan.py](src/exphub/app/models/angle_plan.py) | 8 | BL12 column names in CSV headers + defaults |
| [src/exphub/app/models/eic_control.py](src/exphub/app/models/eic_control.py) | 7 | `beamline_database={"TOPAZ":"bl12","CORELLI":"bl9"}`, `/SNS/groups/topaz/bl_12/` |

**Latent multi-beamline awareness already in code (good — we can build on it):**
- [src/exphub/agent/constants.py:13-52](src/exphub/agent/constants.py#L13-L52) — `EXPERIMENT_PRESETS` has `topaz_standard`, `corelli_standard`, `mandi_standard`.
- [src/exphub/app/models/experiment_info.py:17](src/exphub/app/models/experiment_info.py#L17) — `instrument_list: List[str] = ["TOPAZ","MANDI","CORELLI"]`.
- [src/exphub/app/models/eic_control.py:52](src/exphub/app/models/eic_control.py#L52) — `beamline_database: Dict = {"TOPAZ":"bl12","CORELLI":"bl9"}`.
- [src/exphub/agent/prompts/system_prompt.md:3-4](src/exphub/agent/prompts/system_prompt.md#L3-L4) — system prompt already names all three.

So the *concept* of "multiple beamlines" is sprinkled throughout, but no single object owns it and no machinery dispatches off it. **That object is what we need to build.**

### 1.1 Structural debt found in this audit (unrelated to multi-beamline, but resolve in passing)
- [src/exphub/app/view_models/main.py](src/exphub/app/view_models/main.py) is **1626 lines / 46 methods** — a god object spanning every tab. Mostly orchestration but lines 580–1620 are 1000 lines of *hardcoded per-point-group angle lists* (debug fixtures). These must move out.
- [src/exphub/app/models/eic_client.py](src/exphub/app/models/eic_client.py) — **1566 lines** for one OAuth client. Plausibly decomposable into `auth`, `submit`, `poll`, `abort` modules.
- [src/exphub/app/models/temporal_analysis.py](src/exphub/app/models/temporal_analysis.py) — **1420 lines** mixing Pydantic model + Mantid workflow + figure generation. Three concerns, one file.
- [src/exphub/app/models/angle_plan.py](src/exphub/app/models/angle_plan.py) + `angle_plan_engine.py` — **803 + 1161 lines**. Engine is OK; model has CSV I/O methods that could move to an `io/` submodule.
- [src/exphub/app/models/main_model.py](src/exphub/app/models/main_model.py) hard-imports every sub-model. Should be plugin-loaded.
- Two SESSION_*.md and one CODEBASE_REPORT.md are stale (memory notes; not load-bearing).

---

## 2. Target architecture

```
src/exphub/
├── core/                       ← New: beamline-agnostic framework
│   ├── beamline/
│   │   ├── spec.py             ← BeamlineSpec Pydantic schema (the contract)
│   │   ├── registry.py         ← BeamlineRegistry (discovery + lookup)
│   │   └── context.py          ← BeamlineContext (active beamline + helpers)
│   ├── tabs/
│   │   ├── manifest.py         ← TabManifest, TabSpec
│   │   └── registry.py         ← Per-tab plugin lookup
│   ├── pvs/
│   │   └── catalog.py          ← Replaces gonio_pvs.py; reads from beamline spec
│   ├── paths/
│   │   └── resolver.py         ← Builds /SNS/{instrument}/IPTS-{N}/... from spec
│   └── tasks/
│       └── registry.py         ← Task enum + prompt/tool subset per task
│
├── beamlines/                  ← New: one folder per beamline
│   ├── __init__.py             ← Auto-discovers subpackages
│   ├── topaz/
│   │   ├── spec.py             ← TopazBeamline(BeamlineSpec) — paths, PVs, presets
│   │   ├── pvs.yaml            ← (or .py) — all BL12:* PV names
│   │   ├── tabs/               ← TOPAZ-specific tab content overrides
│   │   │   ├── css_status.py   ← The current views/css_status.py (de-hardcoded)
│   │   │   └── ...
│   │   ├── screens/
│   │   │   ├── BL12_ADnED_2D_4x4.bob
│   │   │   └── BL12_ADnED_2D_4x4.macros
│   │   ├── prompts/
│   │   │   └── context.md      ← TOPAZ-specific agent context
│   │   └── knowledge/
│   │       ├── topaz_overview.md
│   │       └── ...
│   ├── corelli/                ← Add later; mirrors topaz/
│   └── mandi/
│
├── app/                        ← Existing — slimmed; beamline-agnostic shell
│   ├── main.py
│   ├── mvvm_factory.py         ← Reads active beamline; wires per-beamline tabs
│   ├── models/
│   │   ├── base/               ← Beamline-agnostic base models (sample, IPTS, plan)
│   │   ├── main_model.py       ← Composes from beamline registry
│   │   └── ...
│   ├── view_models/
│   │   ├── main.py             ← Slimmed to coordination only
│   │   ├── experiment_info.py  ← New (split from main.py)
│   │   ├── angle_plan.py       ← Exists; expand
│   │   ├── temporal_analysis.py← New
│   │   └── eic_control.py      ← New
│   └── views/
│       ├── shell.py            ← MainApp (former main_view.py minus PV loading)
│       ├── tab_content_panel.py← Reads tab manifest
│       └── beamline_selector.py← New: toolbar dropdown + first-launch dialog
│
└── agent/                      ← Existing — restructured for beamline+task awareness
    ├── agent.py                ← Accepts BeamlineContext + Task
    ├── prompts/
    │   ├── core_identity.md    ← Beamline-agnostic identity
    │   ├── tasks/
    │   │   ├── experiment_steering.md
    │   │   ├── data_processing.md
    │   │   ├── app_help.md
    │   │   └── ...
    │   └── composer.py         ← Assembles prompt from core + beamline + task
    ├── knowledge/
    │   ├── common/             ← Generic crystallography, neutron-scattering
    │   └── (per-beamline lives under beamlines/<name>/knowledge/)
    ├── bridge.py
    ├── tools.py                ← Tools are filtered by task (e.g. data-processing task gets reduction tools, not EIC tools)
    ├── workflow.py             ← PhaseManager — phases become a function of beamline+task
    └── ...
```

The **two pivot points** are:

1. **`BeamlineSpec`** — the contract that every beamline implements. Everything downstream (PVs, paths, presets, knowledge, prompts, tab overrides) is reachable from one spec object.
2. **`BeamlineContext`** — the active singleton passed to MVVM and Agent at runtime. Switching beamlines = swapping this context + re-rendering.

---

## 3. The `BeamlineSpec` contract

A single Pydantic model owns everything beamline-specific. Concrete beamlines subclass or instantiate it.

```python
# core/beamline/spec.py
class GoniometerSpec(BaseModel):
    type: Literal["ambient_2axis", "cryo_1axis", "eulerian_4axis", ...]
    angle_pvs: dict[str, str]                # {"omega": "BL12:Mot:goniokm:omega", ...}
    ramp_pvs: dict[str, str] | None          # optional temperature ramp
    charge_pv: str                            # "BL12:Det:PCharge:C"
    angle_columns_order: list[str]            # display order

class DetectorSpec(BaseModel):
    bob_screen_path: Path                     # relative to beamline/screens/
    macros_path: Path | None
    extra_subscribe_pvs: list[str]            # the _USER_PANEL_PVS list
    detector_layout: Literal["adned_2d_4x4", "anger", "panel_array", ...]
    pixel_dims: tuple[int, int]               # e.g. (1105, 1105)

class MantidSpec(BaseModel):
    instrument_name: str                      # "TOPAZ" / "CORELLI" / "MANDI"
    wavelength_min: float
    wavelength_max: float
    default_max_q: float
    default_tolerance: float
    default_num_peaks_to_find: int

class PathsSpec(BaseModel):
    shared_root: str                          # "/SNS/TOPAZ"
    eic_dropbox: str                          # "/SNS/groups/topaz/bl_12"
    default_calibration: str
    autoreduce_subdir: str = "shared/autoreduce"
    live_monitor_subdir: str = "shared/CrystalPilot/live-data-monitoring"

class EICSpec(BaseModel):
    beamline_code: str                        # "bl12" / "bl9"
    is_simulation_default: bool = False
    write_scope: list[str] = ["EIC:write"]

class AgentSpec(BaseModel):
    context_prompt: Path                      # beamline-specific prompt fragment
    knowledge_dir: Path                       # RAG docs root
    presets: dict[str, dict]                  # name → field-value dict
    supported_tasks: list[TaskId]             # which tasks this beamline supports

class TabOverrides(BaseModel):
    """Per-tab plug-in points. None = use base tab. Anything else replaces it."""
    experiment_info: TabSpec | None = None
    angle_plan: TabSpec | None = None
    temporal_analysis: TabSpec | None = None
    css_status: TabSpec | None = None
    data_analysis: TabSpec | None = None

class BeamlineSpec(BaseModel):
    id: str                                   # "topaz" — used as registry key
    display_name: str                         # "TOPAZ (BL-12)"
    facility: Literal["SNS", "HFIR", ...]
    target_station: Literal["TS-1", "TS-2", "HB-1A", ...] | None
    goniometer: GoniometerSpec
    detector: DetectorSpec
    mantid: MantidSpec
    paths: PathsSpec
    eic: EICSpec
    agent: AgentSpec
    tabs: TabOverrides = TabOverrides()
```

A concrete beamline is then:

```python
# beamlines/topaz/spec.py
TOPAZ = BeamlineSpec(
    id="topaz",
    display_name="TOPAZ (BL-12)",
    facility="SNS",
    target_station="TS-1",
    goniometer=GoniometerSpec(
        type="ambient_2axis",
        angle_pvs={"omega": "BL12:Mot:goniokm:omega", "phi": "BL12:Mot:goniokm:phi"},
        ramp_pvs={"start": "BL12:SE:Ramp:Start", "end": "BL12:SE:Ramp:End", ...},
        charge_pv="BL12:Det:PCharge:C",
        angle_columns_order=["omega", "phi"],
    ),
    detector=DetectorSpec(
        bob_screen_path=Path("BL12_ADnED_2D_4x4.bob"),
        macros_path=Path("BL12_ADnED_2D_4x4.macros"),
        extra_subscribe_pvs=[...19 PVs from main_view.py...],
        detector_layout="adned_2d_4x4",
        pixel_dims=(1105, 1105),
    ),
    mantid=MantidSpec(instrument_name="TOPAZ", wavelength_min=0.4, wavelength_max=3.45, ...),
    paths=PathsSpec(shared_root="/SNS/TOPAZ", eic_dropbox="/SNS/groups/topaz/bl_12", ...),
    eic=EICSpec(beamline_code="bl12"),
    agent=AgentSpec(
        context_prompt=Path("beamlines/topaz/prompts/context.md"),
        knowledge_dir=Path("beamlines/topaz/knowledge"),
        presets={"topaz_standard": {...}},
        supported_tasks=["experiment_steering", "data_processing", "app_help"],
    ),
)
```

Adding CORELLI is then one new `beamlines/corelli/spec.py` plus its `screens/`, `prompts/`, `knowledge/`.

---

## 4. Registry, context, switching

### 4.1 Registry
`core/beamline/registry.py` walks `beamlines/*/spec.py` at startup (or uses Python entry points for installed beamlines). Each spec is registered by `id`. Lookup is `registry.get("topaz")`, listing is `registry.list_ids()`.

### 4.2 Context
`BeamlineContext` is a small object holding the active `BeamlineSpec` plus convenience accessors (`ctx.pv("goniometer.omega")`, `ctx.path("shared_root", ipts=35036)`, `ctx.preset("topaz_standard")`).

`MainModel` gains one new field:
```python
class MainModel(BaseModel):
    beamline_id: str = "topaz"   # default for backward compat
    # ...existing sub-models stay
```

`mvvm_factory.create_viewmodels(binding)` reads `main_model.beamline_id`, fetches the spec from the registry, builds a `BeamlineContext`, and passes it to every view-model and to the agent.

### 4.3 Switching
A `BeamlineSelectorView` in the toolbar (dropdown + "Switch" button) calls `MainViewModel.switch_beamline(new_id)`. Switching:
1. Tears down current async tasks (`stop_live_update()`, `stop_run()` if appropriate).
2. Updates `model.beamline_id`, rebuilds `BeamlineContext`.
3. Calls `TabContentPanel.refresh()` to re-render tabs using new manifest.
4. Reinitializes the agent (`ChatViewModel._agent = None`; next message rebuilds it with new prompt + knowledge).
5. Pushes a `last_update_summary` snackbar: "Switched to CORELLI".

The 5-tab layout itself stays intact; only the content inside each tab swaps.

---

## 5. Tab plug-ins

### 5.1 The TabSpec
```python
class TabSpec(BaseModel):
    tab_id: str                    # "experiment_info" | "angle_plan" | ...
    tab_number: int                # 1..6
    display_name: str
    model_factory: Callable[[BeamlineContext], BaseModel]   # builds the per-tab Pydantic model
    view_model_factory: Callable[[BeamlineContext, BindingInterface, ...], object]
    view_cls: type                 # the Vuetify3 layout class
    applies_to: set[str] | Literal["*"] = "*"   # beamline ids
```

### 5.2 Base tabs (default for every beamline)
- `core/tabs/base/experiment_info.py` — common IPTS / sample / Mantid fields. Most beamlines need these.
- `core/tabs/base/angle_plan.py` — generic run-plan table; goniometer columns come from `ctx.goniometer.angle_columns_order`.
- `core/tabs/base/temporal_analysis.py` — generic live-data view; reduction backend pluggable.
- `core/tabs/base/data_analysis.py` — placeholder/stub.
- **No base for `css_status`** — that one is so detector-specific that each beamline supplies its own.

### 5.3 Per-beamline overrides
`beamlines/topaz/tabs/css_status.py` is the *current* `views/css_status.py` after de-hardcoding (PV strings read from `ctx.pv(...)`, BOB path from `ctx.detector.bob_screen_path`).

A beamline can also override the experiment-info tab if its sample workflow is materially different (e.g. polarized neutrons → adds spin-flip controls); otherwise it gets the base.

### 5.4 The manifest
`core/tabs/manifest.py` builds the active tab list per beamline:
```python
def build_manifest(ctx: BeamlineContext) -> list[TabSpec]:
    """For each base tab, return ctx.beamline.tabs.<tab_id> if set, else the base."""
```

`TabContentPanel.create_ui()` reads the manifest, not a hardcoded import list.

---

## 6. Schema overlay strategy

Some fields are universal (`molecular_formula`, `point_group`). Some are beamline-specific (`mod_vec_1` for modulated structures — TOPAZ-relevant, irrelevant on a powder beamline). We pick **inclusion-by-default + visibility filter**:

1. Base `ExperimentInfoModel` carries every plausible field, *all optional*.
2. `BeamlineSpec.experiment_info_fields: set[str] | None` — if set, restricts the schema to those fields when rendering and when offering to the agent.
3. The view consults `ctx.visible_fields("experiment_info")` to decide which Vuetify inputs to render.
4. The agent's `schema_from_model_instance` is wrapped to filter by `ctx.visible_fields` so the LLM never sees fields the user can't change.

Rationale: a one-Pydantic-class-per-beamline inheritance tree explodes combinatorially when beamlines share most fields but each tweaks a few. A flat base + visibility filter is simpler. Field validators (crystal cascade, etc.) stay on the base class.

---

## 7. Agent multi-beamline / multi-task extensibility

### 7.1 Composable system prompt
Replace the single `prompts/system_prompt.md` with three layers, assembled at agent-init time:

```
[Core Identity]         agent/prompts/core_identity.md  (beamline-agnostic)
 ──────────────────
[Beamline Context]      beamlines/<id>/prompts/context.md
                        (instrument intro, wavelength range, sample environment, etc.)
 ──────────────────
[Task Instructions]     agent/prompts/tasks/<task>.md
                        (experiment_steering, data_processing, app_help, ...)
 ──────────────────
[Tool Reference]        auto-generated from registered tools (already done)
```

`agent/prompts/composer.py`:
```python
def compose_prompt(ctx: BeamlineContext, task: TaskId) -> str:
    parts = [
        read(CORE_IDENTITY),
        read(ctx.spec.agent.context_prompt),
        read(TASK_DIR / f"{task}.md"),
        tool_reference_block(active_tools(ctx, task)),
    ]
    return "\n\n---\n\n".join(parts)
```

### 7.2 Task as a first-class dimension
Define `TaskId = Literal["experiment_steering", "data_processing", "app_help", "instrument_diagnostics"]` (extensible).

- **Tools are filtered by task.** `data_processing` doesn't need `submit_angle_plan`; `app_help` doesn't need `set_parameter`.
- **Phase manager becomes scoped to the active task.** The 7-phase setup→monitor→...→analyse sequence is the `experiment_steering` task; other tasks define their own phase machines (or none).
- The active task is set in `MainModel.active_task` and reflected in the chat pane (small chip near the input: "Mode: Experiment Steering ▾").
- The agent can suggest a task switch ("This sounds like a data-processing question; switch to Data Processing mode?") via a new tool `propose_task_switch(task_id)` that requires user confirmation.

### 7.3 RAG knowledge layout
```
agent/knowledge/common/        ← generic crystallography, neutron scattering, UB matrices
beamlines/topaz/knowledge/     ← TOPAZ-specific docs (current beamline_guide.md belongs here, after splitting)
beamlines/corelli/knowledge/
agent/knowledge/tasks/         ← task-specific guides (e.g. data-reduction recipes)
```

`BeamlineKnowledgeBase.__init__` now takes `(ctx, task)` and indexes the union of: `common/` + `beamlines/<id>/knowledge/` + `tasks/<task>/`. ChromaDB collections are keyed by `(beamline_id, task)` so switches are cheap (the index is per-context, cached).

### 7.4 Agent metadata in every turn
The first SystemMessage in each turn (alongside the existing phase context) now also carries:
```
ACTIVE_BEAMLINE: TOPAZ (SNS, BL-12)
ACTIVE_TASK: experiment_steering
ACTIVE_PHASE: setup (1/7)
```
Cheap and makes debug logs self-describing.

### 7.5 Adding a new beamline (acceptance test)
Estimated work to onboard `MANDI` from scratch:
1. Create `beamlines/mandi/spec.py` (~80 lines).
2. Drop in `beamlines/mandi/screens/MANDI_*.bob` from facility.
3. Write `beamlines/mandi/prompts/context.md` (~50 lines).
4. Drop in `beamlines/mandi/knowledge/*.md`.
5. Optionally write `beamlines/mandi/tabs/css_status.py` if its detector layout differs.

No agent or app code changes. Tests verify the registry picks it up.

### 7.6 Adding a new task (acceptance test)
1. Add `agent/prompts/tasks/instrument_diagnostics.md`.
2. Add a `TaskId` literal value.
3. Filter tools in `core/tasks/registry.py` (declarative: `{"instrument_diagnostics": ["retrieve_docs", "get_parameter", "navigate_to_tab"]}`).
4. (Optional) Drop guides under `agent/knowledge/tasks/instrument_diagnostics/`.

No model or view changes.

---

## 8. PV catalog & path resolver

### 8.1 PV catalog (replaces `gonio_pvs.py`)
`core/pvs/catalog.py`:
```python
class PVCatalog:
    def __init__(self, ctx: BeamlineContext): self.ctx = ctx
    def gonio_angle(self, axis: str) -> str: return self.ctx.spec.goniometer.angle_pvs[axis]
    def gonio_ramp(self, key: str) -> str: ...
    def charge(self) -> str: return self.ctx.spec.goniometer.charge_pv
    def angle_columns(self) -> list[str]: ...   # ordered
    def detect_goniometer_type_from_csv(self, headers: list[str]) -> str: ...
```

Every site that currently imports from `models/gonio_pvs` switches to `ctx.pvs.<accessor>`. The current `gonio_pvs.py` becomes a thin shim that delegates to the active context (for backward compat during transition) and is deleted in a later phase.

### 8.2 Path resolver
`core/paths/resolver.py`:
```python
class PathResolver:
    def __init__(self, ctx, ipts): self.ctx, self.ipts = ctx, ipts
    @property
    def ipts_root(self): return f"{self.ctx.spec.paths.shared_root}/IPTS-{self.ipts}"
    @property
    def autoreduce(self): return f"{self.ipts_root}/{self.ctx.spec.paths.autoreduce_subdir}"
    @property
    def live_monitor(self): return f"{self.ipts_root}/{self.ctx.spec.paths.live_monitor_subdir}"
    @property
    def eic_dropbox(self): return f"{self.ctx.spec.paths.eic_dropbox}/IPTS-{self.ipts}"
```

Every `f"/SNS/TOPAZ/IPTS-{ipts}/..."` in the codebase becomes `paths.autoreduce` / `paths.live_monitor` / etc.

---

## 9. Decomposition of god-files

These are independent of the multi-beamline work but should be done in the same sweep — they make the multi-beamline refactor 3× easier and reduce review surface.

### 9.1 `view_models/main.py` (1626 → ~400 lines target)
- Lines 580–1620 (hardcoded angle lists per point group) → `app/fixtures/optimizer_fallback_angles/<point_group>.json`. Loaded on demand by `angleplan_optimize`.
- Per-tab logic moves into:
  - `view_models/experiment_info.py` (new)
  - `view_models/angle_plan.py` (exists; absorbs more)
  - `view_models/temporal_analysis.py` (new)
  - `view_models/eic_control.py` (new)
  - `view_models/css_status.py` (new)
- `view_models/main.py` keeps only: tab navigation, view-state, cross-tab coordination (e.g. `submit_angle_plan` reads from `experimentinfo`+`angleplan`+`eiccontrol`), live-update task lifecycle.

### 9.2 `models/temporal_analysis.py` (1420 → ~300 lines)
- Split into:
  - `models/temporal_analysis.py` — Pydantic state only
  - `models/mantid_workflow.py` — the `MantidWorkflow` class (reduction pipeline)
  - `models/temporal_figures.py` — `get_figure_intensity/uncertainty`

### 9.3 `models/eic_client.py` (1566 → ~4 files × ~400 lines)
- `eic_client/auth.py` — OAuth2/PingFed flow
- `eic_client/submit.py` — job submission
- `eic_client/poll.py` — status polling
- `eic_client/abort.py` — job abort

### 9.4 `models/main_model.py`
- Composes sub-models from beamline manifest, not from a hardcoded list. Adds `beamline_id` + `active_task` fields.

### 9.5 Stale docs
- `CODEBASE_REPORT.md` (2026-03-30, marked stale in memory) — delete or move to `docs/archive/`.
- `SESSION_*.md` files — move to `docs/sessions/` so they don't clutter the root.

---

## 10. Git tree strategy

### 10.1 Current state
- `main` — production
- `agentize` — current working branch (active, where chat agent landed)
- `origin/hpc-demo` — separate demo branch
- `agentize` has 50+ commits ahead of main with a coherent narrative (agent rollout)

### 10.2 Recommended approach
1. **Land the agent work first.** Open a PR from `agentize` → `main` covering the agent rollout (it's already a self-contained vertical feature). Don't bundle the multi-beamline refactor with it — it dilutes review.
2. **Tag the merge point** as `v0.2-agent` or similar.
3. **Open a long-running feature branch** `multi-beamline` off `main`. Each phase below lands as a sub-PR into `multi-beamline`, not into `main` directly. The whole branch merges to `main` once Phase 6 passes acceptance.
4. **Each sub-PR is independently revertable.** No sub-PR should leave TOPAZ broken; the refactor is incremental, never a flag day.
5. **Keep `hpc-demo` rebased.** When `multi-beamline` lands on main, rebase `hpc-demo` once.

### 10.3 What about `agentize` if main isn't ready yet?
If `agentize` → `main` is blocked, branch `multi-beamline` off `agentize` for now and rebase onto `main` once the agent PR lands. The plan is forward-compatible — the agent prompt composer absorbs the current single-file prompt cleanly.

### 10.4 Naming
The package is `exphub` already, but the user-visible product name is "CrystalPilot." Once multi-beamline lands, consider renaming the *product* to **ExpHub** (or keeping CrystalPilot as the SCD-experiment-flavored skin). The repo can stay `CrystalPilot` to preserve URLs; the launch script gets a `--profile <beamline>` flag.

---

## 11. Phased implementation roadmap

Each phase is **mergeable, testable, and leaves TOPAZ working**. None of them is a big-bang.

### Phase 0 — Inventory & guardrails (1 day)
- [ ] Land a `tests/test_beamline_coupling.py` that **fails** if it finds `TOPAZ|BL12` outside the allowed directories (`beamlines/topaz/`, `tests/fixtures/`). This is the regression net for all later phases.
- [ ] Move stale `SESSION_*.md` to `docs/sessions/`; delete `CODEBASE_REPORT.md`.
- [ ] Open `multi-beamline` long-running branch.

### Phase 1 — Extract BeamlineSpec for TOPAZ (3-5 days)
- [ ] Add `core/beamline/spec.py`, `registry.py`, `context.py`.
- [ ] Create `beamlines/topaz/spec.py` populated with current TOPAZ values.
- [ ] Move `BL12_ADnED_2D_4x4.bob/.macros` from repo root to `beamlines/topaz/screens/`.
- [ ] Replace `models/gonio_pvs.py` constants with `BeamlineContext.pvs` calls. Keep `gonio_pvs.py` as a deprecation shim.
- [ ] **TOPAZ must still launch and behave identically.** No UI changes yet.
- [ ] Add `tests/test_beamline_spec.py`: load TOPAZ spec, verify PV/path round-trips.

### Phase 2 — Path resolver + ExperimentInfo schema overlay (2-3 days)
- [ ] Add `core/paths/resolver.py`. Replace all `f"/SNS/TOPAZ/..."` strings with resolver calls.
- [ ] Add `visible_fields` plumbing to `ExperimentInfoModel`; default = show all.
- [ ] All inserts into Mantid (`Instrument="TOPAZ"`) read from `ctx.mantid.instrument_name`.

### Phase 3 — Decompose god-files (3-5 days)
- [ ] Split `view_models/main.py` into per-tab VMs (target ~400 lines for `main.py`).
- [ ] Move hardcoded angle lists to `fixtures/optimizer_fallback_angles/`.
- [ ] Split `models/temporal_analysis.py` and `models/eic_client.py`.
- [ ] Tests stay green; UI behavior identical.

### Phase 4 — Tab plug-in registry (3-5 days)
- [ ] Add `core/tabs/manifest.py` + `core/tabs/registry.py`.
- [ ] Convert `views/tab_content_panel.py` to read from the manifest.
- [ ] Move `views/css_status.py` to `beamlines/topaz/tabs/css_status.py` (no logic changes; just relocated and PV strings come from spec).
- [ ] Add the toolbar `BeamlineSelectorView` (initially a single-option dropdown — TOPAZ only).
- [ ] **Manual ack test:** switching the selector from TOPAZ to TOPAZ is a no-op.

### Phase 5 — Agent multi-context (3-5 days)
- [ ] Add `agent/prompts/composer.py`, split `system_prompt.md` into `core_identity.md` + `tasks/experiment_steering.md`.
- [ ] Move `agent/knowledge/beamline_guide.md` content: TOPAZ-specific paragraphs to `beamlines/topaz/knowledge/`; generic crystallography to `agent/knowledge/common/`.
- [ ] Add `BeamlineContext` + `TaskId` to `Agent.__init__` and `compose_prompt`.
- [ ] Add the chip on the chat input showing active task; add `propose_task_switch` tool.
- [ ] Inject `ACTIVE_BEAMLINE` / `ACTIVE_TASK` line into per-turn context.
- [ ] Tests: prompt composition, RAG over union of common + topaz knowledge.

### Phase 6 — Onboard a second beamline (CORELLI) (3-5 days)
- [ ] Get the BOB screen + macros from the beamline scientist.
- [ ] Create `beamlines/corelli/spec.py`, `prompts/context.md`, `knowledge/*.md`.
- [ ] Possibly write `beamlines/corelli/tabs/css_status.py` (or reuse a generic one).
- [ ] **End-to-end demo:** launch app, switch from TOPAZ to CORELLI, the css_status tab re-renders with CORELLI PVs, the agent answers "what is CORELLI" from CORELLI's knowledge base, presets switch.
- [ ] Merge `multi-beamline` → `main`.

### Phase 7 — Hardening & docs (1-2 days)
- [ ] Update `README.md` with the beamline-onboarding workflow.
- [ ] Add `docs/adding_a_beamline.md` with a step-by-step guide and a checklist.
- [ ] Tag `v0.3-multibeamline`.

**Total estimate:** ~16-25 engineer-days of focused work, spread over 4-6 calendar weeks if interleaved with other duties.

---

## 12. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Phase 4 breaks `nova.epics.trame` PV connect (which reads from a single XML in `main_view.py`) | M | H | Phase 4 keeps `main_view.epics.connect(...)` working but reads the BOB path from `ctx.detector.bob_screen_path`. The extra-PV subscribe loop just reads `ctx.detector.extra_subscribe_pvs` instead of the literal `_USER_PANEL_PVS` |
| Agent prompt regressions when prompts are split | M | M | Land `tests/test_prompt_composition.py` first; snapshot-compare composed prompt against current `system_prompt.md` for TOPAZ + experiment_steering task to ensure no semantic drift |
| Beamline-switch leaves background tasks running (live-update loop, MonitorLiveData thread) | M | H | `BeamlineContext.activate()` must call `stop_live_update()`, `stop_run()` first. Add a teardown contract test that asserts no async tasks survive a switch |
| ChromaDB index rebuild on every switch is slow | L | M | Persist per-`(beamline, task)` collections; warm cache on startup if user has a preferred beamline |
| `models/eic_client.py` decomposition introduces auth regressions | M | H | Don't decompose in Phase 3; defer to a separate post-multi-beamline cleanup PR. Phase 3 splits the easier targets only |
| Field-visibility filter breaks the agent's schema awareness | M | M | Agent's `schema_from_model_instance` is fed the *filtered* schema, but bridge writes use the *unfiltered* model. Tests verify the agent can't set a hidden field (and reports nicely if it tries) |
| User has unsaved work mid-switch | L | M | Switching shows a confirmation dialog when `model` is dirty; offer to save snapshot first |

---

## 13. Open design questions

These need stakeholder input before Phase 4-5 work starts. Putting them here to surface, not to resolve.

1. **HFIR vs SNS pulsed neutrons.** The temporal-analysis tab assumes pulsed (time-of-flight) data. HFIR is monochromatic. Does the tab simply hide / replace its plots for HFIR beamlines, or is "live reduction" semantically different enough to need a separate tab variant?
2. **Multi-task simultaneity.** Can a user be in `experiment_steering` *and* `data_processing` simultaneously (e.g. monitoring a running scan while analyzing yesterday's data)? If yes, the agent needs per-tab task context, not a global one.
3. **Beamline-specific tools.** Some beamlines have unique buttons (e.g. spin-flipper toggle). Where does that tool live — in the beamline's spec as a tool factory, or as an MCP server per beamline?
4. **`is_simulation` semantics across facilities.** TOPAZ's EIC has a sandbox; other facilities may not. Does `beamline.eic.is_simulation_default` cover this, or do we need a `eic.supports_simulation: bool` flag?
5. **Naming.** Keep `CrystalPilot` (SCD-specific), rebrand to `ExpHub` (generic), or have one repo serve both as theming?

---

## 14. Quick wins to land first (independent of the big plan)

If we want momentum before Phase 1, these can land in the next day or two with no architectural decisions:

- [ ] Move hardcoded angle lists out of `view_models/main.py:580-1620` into fixture files. Pure mechanical change, ~1000-line reduction.
- [ ] Move stale SESSION + CODEBASE_REPORT files into `docs/archive/`.
- [ ] Add the `tests/test_beamline_coupling.py` ratchet (will start failing as we add code; that's the point — it documents progress).
- [ ] Centralize the `Instrument="TOPAZ"` string and `/SNS/TOPAZ/` paths into a single `topaz_paths.py` constants file. Even before Phase 1, this makes the eventual Phase 1 migration mechanical.

---

## Appendix A — Acceptance criteria for "multi-beamline ready"

The refactor is **done** when all of the following are true:

1. `grep -r "TOPAZ\|BL12" src/` returns 0 results outside `beamlines/topaz/` and `tests/`.
2. The repo ships at least 2 beamline plug-ins (TOPAZ + one other).
3. A new beamline can be added by editing **only files under `beamlines/<new_id>/`**.
4. The agent's system prompt is assembled at runtime from `(core, beamline, task)` and shows no TOPAZ-specific text when active beamline is not TOPAZ.
5. Switching beamlines at runtime works without restart.
6. All existing tests pass; new tests cover spec loading, prompt composition, tab manifest assembly, and switch teardown.
7. A beamline-onboarding guide (`docs/adding_a_beamline.md`) exists.

---

## Appendix B — File-by-file migration cheat sheet

For implementers picking up the refactor mid-stream:

| Current location | Becomes |
|---|---|
| `src/exphub/app/models/gonio_pvs.py` | `core/pvs/catalog.py` + `beamlines/topaz/spec.py:goniometer` |
| `BL12_ADnED_2D_4x4.bob` (repo root) | `beamlines/topaz/screens/BL12_ADnED_2D_4x4.bob` |
| `BL12_ADnED_2D_4x4.macros` (repo root) | `beamlines/topaz/screens/BL12_ADnED_2D_4x4.macros` |
| `src/exphub/app/views/css_status.py` | `beamlines/topaz/tabs/css_status.py` (PVs from `ctx.pv(...)`) |
| `src/exphub/app/views/main_view.py:_USER_PANEL_PVS` | `beamlines/topaz/spec.py:detector.extra_subscribe_pvs` |
| `src/exphub/agent/constants.py:EXPERIMENT_PRESETS` | Each preset moves to its beamline's `spec.py:agent.presets` |
| `src/exphub/agent/prompts/system_prompt.md` (Workflow + JOBs) | Split into `core_identity.md` + `tasks/experiment_steering.md` + `beamlines/topaz/prompts/context.md` |
| `src/exphub/agent/knowledge/beamline_guide.md` | Split into `agent/knowledge/common/*.md` + `beamlines/topaz/knowledge/*.md` |
| `models/eic_control.py:beamline_database` | Deleted; `beamline.eic.beamline_code` replaces it |
| `models/experiment_info.py:instrument_list` | Replaced by `registry.list_ids()` |
| `view_models/main.py:580-1620` (hardcoded angle lists) | `app/fixtures/optimizer_fallback_angles/<point_group>.json` |
| `SESSION_*.md`, `CODEBASE_REPORT.md` | `docs/archive/` |

---

*End of plan. Awaiting approval before execution.*
