# CrystalPilot: Multi-Technique Refactoring Plan

**Author:** generated 2026-06-02 from a 10-agent audit + critique workflow
**Branch state:** active branch `multibeamline`; this work extends the
already-landed multi-beamline architecture (see `MULTI_BEAMLINE_PLAN.md`).
**Scope:** Lift the implicit "single-crystal diffraction" assumption out of
`app/` and core. Move single-crystal-shaped models, view-models, and views
into a per-technique package. Introduce a SANS technique package and onboard
USANS (SNS BL-1A) as a beamline plug-in. Tabs 1-3 become technique-default
with optional per-beamline override; tabs 4-5 become per-beamline-required.

## Why now

The multi-beamline refactor (May 2026) made every per-instrument *parameter*
plug-in: PV names, file paths, instrument id, BOB screens, agent prompts.
It assumed the *shape* of every tab was shared. TOPAZ and CORELLI fit that
assumption — both are single-crystal-diffraction instruments. USANS does
not: it has no goniometer, no UB matrix, no peak selection. Its tabs need
genuinely different models, view-models, and views — not just different
values for the existing fields.

The current spec encodes per-beamline values for a fixed shape. No amount
of new `BeamlineSpec` fields will make tab 1 stop demanding crystal-system /
point-group / centering / UB, or make tab 2 stop running peak-integration
Mantid pipelines. The shape itself has to become plug-in-shaped.

## Target architecture

```
src/exphub/
├── core/                    # cross-technique, cross-beamline
│   ├── beamline/            # Spec, Registry, Context, Technique enum
│   ├── paths/               # PathResolver
│   ├── eic/                 # EIC client + control model (decomposed)
│   └── (future shared concerns)
├── techniques/              # NEW — technique-family implementations
│   ├── __init__.py          # TECHNIQUE_REGISTRY (lazy importlib discovery)
│   ├── single_crystal/      # ~90% of today's app/ moves here
│   │   ├── manifest.py
│   │   ├── models/
│   │   ├── view_models/
│   │   ├── views/
│   │   ├── agent/           # SC-specific PhaseManager phases, prompts
│   │   └── prompts/
│   └── sans/                # NEW for USANS (and future GP-SANS, EQ-SANS)
│       ├── manifest.py
│       ├── models/
│       ├── view_models/
│       ├── views/
│       ├── agent/
│       └── prompts/
├── beamlines/
│   ├── topaz/               # technique="single_crystal"
│   ├── corelli/             # technique="single_crystal"
│   └── usans/               # NEW: technique="sans"
└── app/                     # tab shell only; technique-agnostic
    ├── views/main_view.py
    ├── views/tab_content_panel.py    # manifest-driven dispatcher
    ├── views/tabs_panel.py
    ├── views/chat_pane.py
    ├── view_models/
    │   ├── app_shell.py     # NEW slim AppShell VM
    │   └── chat.py
    ├── models/
    │   └── main_model.py    # thin: shell fields + technique-supplied root
    └── main.py
```

### Boundary rule

| Layer | Holds | Stays at refactor |
|---|---|---|
| `core/` | Anything *every neutron experiment* has: paths, EIC plumbing, monitor PVs, registry, spec, agent runtime | Yes |
| `techniques/<id>/` | Anything *every beamline of this family* shares: models, view-models, default tab views, PhaseManager phases, prompt fragment, action tools, RAG corpus | NEW |
| `beamlines/<id>/` | Per-beamline parameters + required per-beamline tabs 4-5 + optional overrides of tabs 1-3 | Largely unchanged |
| `app/` | Window chrome, tab navigation, beamline selector, chat panel — technique-agnostic | Slimmed down |

### Tab fall-through contract

```
tab_content_panel.py for tab_key:
    factory = beamline.tabs[tab_key]
    if factory is None and tab_key in {ipts, live, steering}:
        factory = technique.default_tabs[tab_key]
    if factory is None and explicitly opted into optional default:
        factory = technique.optional_tab_defaults[tab_key]
    if factory is None:
        render PlaceholderTab(message=beamline.placeholder_message[tab_key],
                              links=beamline.placeholder_links[tab_key])
    else:
        wrap in v_if="controls.active_tab_key == <key>"; call factory(...)
```

- **Tabs 1-3 (ipts, live, steering):** technique provides default; beamline
  may override.
- **Tabs 4-5 (status, analysis):** technique provides no default; beamline
  may either ship its own factory **or** opt into `technique.optional_tab_defaults`
  (e.g. MANDI re-using TOPAZ's data-analysis launcher) **or** fall through
  to a richer placeholder with optional message + external links.
- **Atomic factory swap only.** A beamline does not compose a default
  + a custom widget. If finer parameterisation is needed, the technique
  view reads it from `BeamlineSpec.technique_config`.

### Spec evolution: discriminated union, not Optional fields

```python
class BeamlineSpec(BaseModel):
    # Cross-technique core
    id: str
    facility: str
    target_station: str | None
    technique: Literal["single_crystal", "sans"]   # discriminator
    paths: PathsSpec
    detector_monitor_pvs: dict[str, str]
    eic: EICSpec                                   # auth + dropbox + server_url
    agent: AgentSpec
    tabs: TabOverrides
    external_links: dict[str, str]
    placeholder_messages: dict[TabKey, str] = {}
    placeholder_links: dict[TabKey, list[tuple[str, str]]] = {}
    # Discriminated technique payload
    technique_config: SingleCrystalConfig | SansConfig = Field(discriminator="kind")


class SingleCrystalConfig(BaseModel):
    kind: Literal["single_crystal"] = "single_crystal"
    goniometer: GoniometerSpec
    mantid: MantidSpec             # instrument_name, wavelength range,
                                    #   default_max_q, tolerance, num_peaks
    default_calibration: str
    default_spectra: str
    run_title_pv: str
    bob_screen_path: Path | None = None
    bob_macros_path: Path | None = None
    extra_subscribe_pvs: list[str] = []

class SansConfig(BaseModel):
    kind: Literal["sans"] = "sans"
    mantid_instrument_name: str | None = None      # may not use Mantid
    default_q_range: tuple[float, float] | None = None
    transmission_monitor_pv: str | None = None
    live_stream_url: str | None = None              # to-be-determined
    # USANS-specific extras land here
```

This is mypy-checkable (the discriminator narrows the union at every read
site) and explicit (a reflectometry author in 18 months sees what each
technique family carries instead of a wall of `Optional[GoniometerSpec]`).

### Technique manifest

```python
class TechniqueManifest(BaseModel):
    id: str
    display_name: str
    default_tabs: dict[TabKey, TabFactory]        # tabs 1-3
    optional_tab_defaults: dict[TabKey, TabFactory]  # tabs 4-5 "common-useful"
    phases: list[PhaseDefinition]                  # for PhaseManager
    bridged_submodels: tuple[str, ...]            # for agent/bridge.py
    action_tools: list[ActionTool]                 # technique-specific agent verbs
    tab_aliases: dict[str, TabKey]                 # NL → tab key for the LLM
    tab_labels: dict[TabKey, str]                  # user-visible labels
    prompts_dir: Path                              # for compose_system_prompt
    knowledge_dir: Path                            # for RAG
    eic_row_builder: Callable                      # technique-specific CSV row shape
    root_model_factory: Callable[[], BaseModel]    # contributes the technique sub-model
```

The manifest is **the** plug-in point; no single-crystal vocabulary leaks
into `app/` or `core/` once the refactor finishes.

### TabKey enum (replaces integer 1,2,3,5,6 today)

```python
class TabKey(str, Enum):
    IPTS = "ipts"
    LIVE = "live"
    STEERING = "steering"
    STATUS = "status"
    ANALYSIS = "analysis"
```

Trame `v_if` predicates keep using ints at the dispatcher layer
(`v_if="controls.active_tab == 0"`); the agent and the manifest speak
`TabKey`. `navigate_to_tab` accepts a `TabKey` string; integer addressing
removed from the agent's tool docstring (the LLM literally sees the
technique-active tab list).

### Agent multi-technique parametrisation

| Concern | Today | After P1 |
|---|---|---|
| Prompt composition | `core_identity + beamline_context + task` | `core_identity + technique_context + beamline_context + task` |
| PhaseManager phases | Hardcoded 7 SC phases in `agent/workflow.py` | Loaded from active manifest |
| BRIDGED_SUBMODELS | Module-level constant in `agent/bridge.py` | Read from active manifest |
| FIELD_OWNER | Hardcoded `point_group`, `instrument` keys | Read from active manifest |
| ACTION_FNS in chat VM | Hardcoded 5 SC verbs | Manifest-driven; technique declares its action tools |
| TAB_MAP / TAB_NAMES | Module-level dict with SC labels | `tab_aliases` + `tab_labels` on manifest |
| RAG corpus | One global ChromaDB collection | Per-technique sub-collection; switched on `set_active` |
| Schema rebuild on switch | Never happens (`schema_properties` frozen at first message) | `Agent.rebuild_schema(main_model)` on inside-technique switch |

### Cross-technique switching: gated to require restart in v1

Today's `switch_beamline` flips the registry and shows a "restart required"
snackbar. Inside-technique (TOPAZ ↔ CORELLI) is mildly broken (EPICS subs,
RAG, model defaults don't fully re-roll). Cross-technique (TOPAZ ↔ USANS)
silently breaks 7 systems at once. **The beamline selector gates
cross-technique options** (grayed-out with banner "Restart CrystalPilot to
switch technique families") in v1. A future P3a-future phase tackles true
hot-rebuild (drop agent, rebuild model, instantiate new technique VM with
`on_deactivate()` lifecycle hook).

---

## Phase plan

Each phase has explicit deliverables, test gates, and rollback story. Phases
land as separate PRs; multiple PRs per phase if scope requires it.

### P0 — Plan + ratchets + safety nets

**Goal:** lock the contract before any code moves; install regression
ratchets that will keep P1–P6 honest.

Deliverables:

1. `MULTI_TECHNIQUE_PLAN.md` (this file)
2. Cross-link banners on `MULTI_BEAMLINE_PLAN.md`, `README.md`, key session
   logs, archived `CODEBASE_REPORT.md`
3. `tests/test_technique_coupling.py` — regression ratchet that scans
   `src/exphub/app/` and `src/exphub/core/` for single-crystal identifiers
   (`crystalsystem`, `point_group`, `centering`, `UB`, `HKL`, `MNP`, `peak`,
   `Bragg`, `max_q`, `d_min`/`d_max`, `angle_plan`, `temporal_analysis`,
   `gonio_pvs`, ...). Initial baseline count committed; **must reach 0 by
   end of P2** before P3 starts
4. `tests/test_tab_overrides.py` — tab-content fall-through contract test
   (today: css_status override path; rest land green as P3 dispatcher
   generalises)
5. `gonio_pvs.py` startup guard — wrap module-import-time
   `importlib.import_module` in try/except returning a stub when the active
   beamline has no `gonio.py`. **This is a USANS-startup-crash hazard
   today.**
6. `TabOverrides` field type tightening — `Any` → `Optional[Callable[[Any], object]]`
7. Cleanup: delete `tests/test-vdatatable.py`, `tests/php`, move
   `tests/datatable.py` to `examples/`
8. Session log: `docs/sessions/SESSION_2026-06-XX-multitechnique-P0.md`

Test gate: ratchet committed with initial count; new tab-overrides test
covers the existing css_status path; all 102+ existing tests green.

Rollback: each item is independently revertible.

### P0.5 — Spec discriminator split (PRE-MOVE)

**Goal:** migrate `BeamlineSpec` to the discriminated-union shape *before*
moving files, so the call-site updates land alongside the spec shape change
rather than during P2's churn.

Deliverables:

1. Define `SingleCrystalConfig` (currently inlined as `GoniometerSpec`,
   `MantidSpec`, `paths.default_calibration`, `paths.default_spectra`,
   `eic.run_title_pv`, `detector.bob_screen_path`/`macros_path`/`extra_subscribe_pvs`)
2. Migrate TOPAZ + CORELLI specs to set `technique="single_crystal"` and
   carry their existing values under `technique_config: SingleCrystalConfig`
3. Update all 14 single-crystal-assumed `active().X` call sites to read
   through the discriminator (e.g. `spec.technique_config.goniometer.angle_pvs`
   instead of `spec.goniometer.angle_pvs`)
4. Add minimal `SansConfig` stub for shape parity (no USANS spec yet — that's P5)
5. Tests for the discriminated-union resolution (mypy clean, runtime narrows)

Test gate: all 102+ tests green; `mypy` clean on `core/beamline/spec.py`.

Rollback: this is a single PR; revert if anything breaks.

### P1 — Technique manifest + agent parametrisation (additive)

**Goal:** introduce the technique layer without moving any code yet. Make
the agent stop hardcoding single-crystal everything.

Deliverables:

1. `core/beamline/technique.py`:
   - `TabKey` enum
   - `TabFactory` protocol
   - `PhaseDefinition`, `ActionTool` dataclasses
   - `TechniqueManifest` Pydantic model
   - `TECHNIQUE_REGISTRY` module-level registry
   - `register_technique(manifest)`, `get_technique(id)`, lazy
     `importlib.import_module(f'exphub.techniques.{id}')` on first access
2. `BeamlineSpec.technique: Literal[...]` — defaults to `"single_crystal"`
   so TOPAZ/CORELLI specs don't need editing
3. `techniques/single_crystal/manifest.py` — declares default tabs 1-3 by
   lazy-importing the existing views from `app/views/`. Tabs 4-5 default to
   None.
4. `compose_system_prompt` becomes 3-layer: `core_identity → technique_context
   → beamline_context → task`. `techniques/<id>/prompts/context.md` holds
   the technique fragment.
5. `PhaseManager(__init__)` accepts a `list[PhaseDefinition]`; the existing
   7-phase list moves to `techniques/single_crystal/agent/phases.py`
6. `agent/bridge.BRIDGED_SUBMODELS` and `FIELD_OWNER` read from the active
   manifest
7. `ChatViewModel._build_action_fns` reads from `manifest.action_tools`;
   `agent/tools.py` shrinks to the generic 7 tools
8. `Agent.rebuild_schema(main_model)` exists; called from `switch_beamline`
   on inside-technique switch (no schema change yet, but the plumbing is
   there for v1's "restart required for cross-technique" gate)
9. `navigate_to_tab` accepts a `TabKey` string; integer aliases retained as
   a translation shim only
10. Test refactor: existing `test_app.py`/`test_model.py`/`test_agent.py`
    updated to use the future access pattern (e.g.
    `model.technique.experimentinfo.crystalsystem`) even though the
    composition is still flat — this lets P2 file moves stay green at every
    commit
11. `tests/test_viewmodel_surface.py` — contract test asserting expected
    `*_bind` attributes are exposed on the technique VM (will be wired in
    P2; lands here with the SC bind names to lock the contract)

Test gate: all existing tests still pass; new manifest tests pass; ratchet
count unchanged (no app/core code moved yet).

### P2 — Move single-crystal code (one file per commit + shims)

**Goal:** physically relocate single-crystal-specific code under
`techniques/single_crystal/`, with mid-P2 rollback always one revert away.

Policy: each commit moves **one** module under
`techniques/single_crystal/<area>/<file>.py` AND leaves a re-export shim at
the old `app/<area>/<file>.py` location. Shim deletion is a single
dedicated cleanup commit at the END of P2.

Order of moves (each is one commit):

```
P2.1   app/models/experiment_info.py        → techniques/single_crystal/models/
P2.2   app/models/angle_plan.py             → techniques/single_crystal/models/
P2.3   app/models/angle_plan_engine.py      → techniques/single_crystal/models/
P2.4   app/models/temporal_analysis/        → techniques/single_crystal/models/
P2.5   app/models/css_status.py             → techniques/single_crystal/models/
P2.6   app/models/data_analysis.py          → techniques/single_crystal/models/
P2.7   app/models/newtabtemplate.py         → techniques/single_crystal/models/
P2.8   app/models/gonio_pvs.py              → techniques/single_crystal/models/
P2.9   agent/validation.py                  → techniques/single_crystal/agent/validation.py
P2.10  app/view_models/angle_plan.py        → techniques/single_crystal/view_models/
P2.11  app/views/experiment_info.py         → techniques/single_crystal/views/
P2.12  app/views/angle_plan.py              → techniques/single_crystal/views/
P2.13  app/views/temporal_analysis.py       → techniques/single_crystal/views/
P2.14  app/views/data_analysis.py           → techniques/single_crystal/views/
P2.15  app/views/newtabtemplate.py          → techniques/single_crystal/views/
P2.16  view_models/main.py decomposition (see below)
P2.17  app/fixtures/optimizer_fallback_angles.json → techniques/single_crystal/fixtures/
P2.18  delete all re-export shims (cleanup)
```

P2.16 is the hard one: **one-shot rename** `MainViewModel` →
`SingleCrystalSteeringViewModel`, plus extract a new slim `AppShellViewModel`
class (not a rebranded old class). No "delegator shim" — the rename touches
every view file, every test, and the TOPAZ tabs/css_status.py, in one
commit. ViewState splits: `AppShellViewState` (active_tab, beamline_id,
beamline_options, beamline_switch_*) + `SingleCrystalSteeringViewState`
(hkl_individual_menu, hkl_peak_ratio_menu, is_live_update_running).

Test gate: ratchet count strictly decreases per commit; reaches **zero**
at P2.18. Trame-bind-surface snapshot unchanged at every commit. All
existing tests pass at every commit.

Rollback: single-commit revert.

### P3 — Manifest-driven dispatcher

**Goal:** turn the tab plumbing inside-out — `TabContentPanel` consults
the manifest instead of hardcoding imports.

Deliverables:

1. `tab_content_panel.py` iterates `TechniqueManifest.default_tabs` +
   `BeamlineSpec.tabs` for all 5 slots uniformly; uses `v_if` (not
   `v_show`) so factories are called only on first navigation
2. `PlaceholderTab` view with `message` + `external_links` parameters
3. CORELLI ships `beamlines/corelli/tabs/data_analysis.py` (currently uses
   the shared view, would regress to placeholder otherwise)
4. Beamline selector **gated to within-technique**: cross-technique
   options grayed-out with banner. Switching requires restart.
5. `switch_beamline` calls `active_technique_vm.on_deactivate()` (cancels
   live-update task, clears temporal buffers, disconnects binds) on
   inside-technique switch

Test gate: `test_tab_overrides.py` passes for TOPAZ + CORELLI; all 5 slots
round-trip via manifest. Ratchet stays at zero.

### P3a — Decompose EIC into core/

**Goal:** prepare for SANS to submit through the same EIC pipeline with a
different row-builder and server address.

Deliverables:

1. `core/eic/eic_client.py` (relocated from `app/models/eic_client.py`)
2. `core/eic/control.py` (relocated from `app/models/eic_control.py`,
   stripped of single-crystal CSV column logic)
3. `EICRowBuilder` protocol on `TechniqueManifest`:
   - `build_rows(strategy_rows, ipts, spec) -> (headers: list[str], rows: list[list])`
4. `techniques/single_crystal/agent/eic_row_builder.py` — produces the
   current 6-angle+ramp+title CSV row shape
5. `EICSpec.server_url: str` field added (every beamline has its own EIC
   server address per user's answer)
6. `test_beamline_coupling.py` allow-list re-evaluated; `eic_client.py`
   move probably removes the special-case

Test gate: EIC tests still pass; SC submissions still work end-to-end via
the new RowBuilder seam.

### P4 — SANS technique skeleton

**Goal:** ship the SANS technique package with placeholder content. No
USANS spec yet.

Deliverables:

1. `techniques/sans/manifest.py` — declares default tabs 1-3 with SANS
   shapes (no UB, no HKL, no peak selection, no coverage)
2. `techniques/sans/models/`:
   - `ipts_info.py` — sample-info fields only (no crystal system / point
     group / centering / UB / d-spacing)
   - `strategy.py` — CSV-loadable editable table; TOPAZ-shaped row schema
     with different column names (column names TBD with user)
   - `iq_reduction.py` — placeholder; prediction-model dropdown stays "TBD"
     until SANS pipeline is specified
3. `techniques/sans/view_models/steering.py` — SANS-specific orchestration
4. `techniques/sans/views/` — tab 1, 2, 3 views in SANS shape
5. `techniques/sans/agent/phases.py` — SANS phase list (e.g. setup,
   configure_q_range, load_strategy, monitor_reduction, save)
6. `techniques/sans/prompts/context.md` — "you are operating a SANS
   instrument; UB matrices are not applicable; reduction produces I(Q)"
7. `techniques/sans/agent/eic_row_builder.py` — SANS CSV row shape (TBD)
8. `tests/test_multi_technique.py` end-to-end:
   - `set_active("topaz")` → tab 1 model has `crystalsystem`
   - `set_active("usans")` (test stub spec) → tab 1 model has no `crystalsystem`
   - Cross-technique switching is gated (selector shows banner)

Test gate: SANS skeleton tests green; existing 102+ tests still green.

### P5 — USANS beamline plug-in

**Goal:** ship USANS as a `beamlines/usans/` plug-in.

Deliverables:

1. `beamlines/usans/__init__.py` — `register(USANS)`
2. `beamlines/usans/spec.py`:
   - `technique="sans"`, `technique_config=SansConfig(...)`
   - `paths=PathsSpec(shared_root="/SNS/USANS", ...)`
   - `eic=EICSpec(beamline_code="bl1a", server_url="<USANS EIC server>")`
   - `placeholder_messages={TabKey.STATUS: "...", TabKey.ANALYSIS: "..."}`
   - `placeholder_links={...}`
3. `beamlines/usans/prompts/context.md`
4. `beamlines/usans/knowledge/usans_overview.md`
5. `beamlines/__init__.py` adds `from . import usans`
6. (Optional, when content available) `beamlines/usans/tabs/instrument_status.py`,
   `beamlines/usans/tabs/data_analysis.py`. Until then, USANS uses
   placeholder with `placeholder_message` + `placeholder_links` directing
   to the appropriate Mantid GUI / web tool.

Test gate: `tests/test_multi_technique.py` runs with real USANS spec;
ratchet stays at zero.

### P6 — Docs + acceptance

Deliverables:

1. `docs/adding_a_technique.md` — onboarding guide for a new technique
   family. Worked example: reflectometry.
2. `docs/adding_a_beamline.md` — rewritten for the new world. Decision
   tree: extend existing technique vs add a new technique. Worked example:
   GP-SANS (same technique as USANS).
3. `docs/architecture/` — short overview pages: one per layer
   (core, techniques, beamlines, app, agent). Each ≤200 words plus a
   diagram.
4. Acceptance check (analogous to MULTI_BEAMLINE_PLAN.md Appendix A):
   - ✅ `grep -rn 'crystalsystem\|point_group\|UB\|HKL' src/exphub/app/ src/exphub/core/`
     returns 0 results
   - ✅ Repo ships single_crystal + sans techniques
   - ✅ Adding a new technique requires only `techniques/<id>/` files
   - ✅ Adding a new beamline of an existing technique requires only
     `beamlines/<id>/` files
   - ✅ Cross-technique switching is gated to restart-required
   - ✅ Agent's `set_parameter` exposes only technique-relevant fields after
     restart-switch
   - ✅ All 102+ tests green

### P3a-future — True cross-technique hot-rebuild

**Deferred until v2.** Lifts the "restart required for cross-technique"
gate. Implements `switch_beamline` rebuild:

1. Detect cross-technique switch
2. `active_technique_vm.on_deactivate()` — cancel async tasks, clear
   buffers, disconnect binds
3. Drop the active agent (forces lazy re-init with new schema)
4. Swap `MainModel.technique` to the new technique's root sub-model
5. Instantiate the new technique VM, register its binds
6. Re-resolve TabContentPanel slots from the new manifest
7. Notify the user via a snackbar (not a confirm dialog — user already
   confirmed via the new selector UX)

---

## Invariants (must hold at every commit P0 → P6)

1. `MainApp()` constructs without error for every `(active_beamline,
   technique)` pair in CI
2. Every trame binding namespace string used by any view module continues
   to resolve (snapshot test enforces, lands in P0)
3. Every entry in the active manifest's `bridged_submodels` exists as an
   actual attribute on the technique's `MainModel` composite (parametrized
   test, lands in P1)
4. `test_technique_coupling.py` ratchet count strictly decreases per commit
   during P2; reaches **zero by end of P2**; **CI gate before P3**
5. `test_beamline_coupling.py` stays at zero (no regression)
6. All 102+ existing tests green at every commit (P1 updates them to the
   future access pattern so P2 doesn't churn them)

## Decisions resolved (recorded for future reference)

| # | Question | Decision | Source |
|---|---|---|---|
| 1 | EIC for SANS | Same EIC module for all beamlines; different RowBuilder + server address per beamline | User, 2026-06-02 |
| 2 | Technique id naming | `"single_crystal"` for now; accept imprecision (CORELLI diffuse scattering, future Laue distinctions) until a concrete need to refactor | User, 2026-06-02 |
| 3 | TabOverrides composition policy | Atomic factory swap only — no per-section composition. Beamline-level customisation goes through `BeamlineSpec.technique_config` | User, 2026-06-02 |
| 4 | Cross-technique switching | Require restart in v1. Beamline selector gates cross-technique options with banner. True hot-rebuild deferred to P3a-future | User, 2026-06-02 |
| 5 | USANS strategy file format | CSV, TOPAZ-shaped, different column names (to be specified when SANS skeleton lands) | User, 2026-06-02 |
| 6 | Live-stream URL location | Unknown; `SansConfig.live_stream_url: Optional[str] = None` placeholder until specified | User, 2026-06-02 |

## Related work

This design is closer to a typed plug-in registry than to BlueSky's
`RunEngine.subscribe(callback)` interface (Python callables, not just
event handlers) or Mantid's facility/instrument XML (declarative, runtime
parsed). The trame state-synchronisation layer requires typed binding
paths, which makes Pydantic specs + Python factory callables a better fit
than a YAML/XML approach. The two-level layering (beamline + technique)
mirrors Mantid's facility-XML/instrument-XML two-level hierarchy, just
implemented at the application layer rather than the file format.

## Notes on risk

The 10-agent audit + critique workflow flagged several issues that this
plan now addresses explicitly:

- **gonio_pvs.py startup crash on USANS** — P0 wraps the module-import-time
  `importlib.import_module` in a guard. Without this fix, USANS-active
  startup fails before `MainApp()` runs.
- **Trame template binding namespaces are an undocumented public API** —
  P0 adds a snapshot test before any moves.
- **MainViewModel as universal contract** — every view imports it by name.
  P2.16 does a one-shot rename (no delegator) so views update once and stay
  stable.
- **22 Optional spec fields = tech-debt time-bomb** — P0.5 uses a
  discriminated union instead. New techniques get clean configs from day one.
- **Tab numbering inconsistency (1,2,3,5,6 — gap at 4)** — P1 switches to
  `TabKey` string IDs at the manifest + agent layers.
- **Agent BRIDGED_SUBMODELS / PHASES / action_fns are hardcoded SC** — P1
  parametrises all three through the manifest, so USANS doesn't need
  agent-side patches.
- **RAG corpus is technique-mixed** — addressed in P1: per-technique
  knowledge dir, ChromaDB filter or sub-collection on `set_active`.

## File-by-file disposition cheat sheet

| Current path | Layer | Target path |
|---|---|---|
| `app/main.py`, `app/__main__.py`, `app/main_view.py`, `app/tabs_panel.py`, `app/chat_pane.py`, `app/md_render.py` | app_shell | unchanged |
| `app/mvvm_factory.py` | app_shell | unchanged (composition rewired) |
| `app/models/main_model.py` | app_shell | unchanged; refactored to compose technique-provided root |
| `app/models/chat.py` | app_shell | unchanged |
| `app/view_models/chat.py` | app_shell | unchanged; BRIDGED_SUBMODELS comes from manifest |
| `app/views/tab_content_panel.py` | app_shell | unchanged (rewired to manifest in P3) |
| `app/views/eic_control.py` | app_shell (currently dead) | unchanged; submit-button wired to manifest action |
| `app/models/experiment_info.py` | technique_single_crystal | `techniques/single_crystal/models/` |
| `app/models/angle_plan.py`, `angle_plan_engine.py` | technique_single_crystal | `techniques/single_crystal/models/` |
| `app/models/temporal_analysis/*` | technique_single_crystal | `techniques/single_crystal/models/temporal_analysis/` |
| `app/models/css_status.py`, `data_analysis.py`, `newtabtemplate.py` | technique_single_crystal | `techniques/single_crystal/models/` |
| `app/models/gonio_pvs.py` | technique_single_crystal | `techniques/single_crystal/models/` |
| `app/models/eic_control.py` | core | `core/eic/control.py` (split: protocol + impl) |
| `app/models/eic_client.py` | core (vendored) | `core/eic/eic_client.py` |
| `app/view_models/main.py` | mixed | split: `app/view_models/app_shell.py` + `techniques/single_crystal/view_models/steering.py` |
| `app/view_models/angle_plan.py` | technique_single_crystal | `techniques/single_crystal/view_models/` |
| `app/views/{experiment_info,angle_plan,temporal_analysis,data_analysis,newtabtemplate}.py` | technique_single_crystal | `techniques/single_crystal/views/` |
| `agent/validation.py` | technique_single_crystal | `techniques/single_crystal/agent/validation.py` |
| `agent/workflow.py` (PHASES table) | technique_single_crystal | `techniques/single_crystal/agent/phases.py` (machine stays in agent/) |
| `agent/constants.py` (TAB_MAP, TAB_NAMES) | technique_single_crystal | move to manifest fields |
| `agent/bridge.py` (BRIDGED_SUBMODELS, FIELD_OWNER) | core | constants drop; values come from manifest |
| `core/beamline/*`, `core/paths/*` | core | unchanged |
| `beamlines/topaz/*`, `beamlines/corelli/*` | beamline_plugin | spec migrated to discriminated config (P0.5) |
| `beamlines/usans/` | beamline_plugin | NEW (P5) |
| `tests/*` | test | most unchanged; new ratchet + multi-technique tests; SC-specific tests moved under `tests/techniques/single_crystal/` |

---

## Session-by-session execution plan

| Session | Phase(s) | Major deliverables |
|---|---|---|
| 1 | P0 | This plan; ratchet test; gonio guard; type tightening; cleanup; session log |
| 2 | P0.5 | Spec discriminated union; TOPAZ + CORELLI specs migrated |
| 3 | P1.a | Technique enum + manifest + registry; BeamlineSpec.technique field; SC manifest stub re-exporting current views |
| 4 | P1.b | Agent parametrisation: PhaseManager, prompt composer, BRIDGED_SUBMODELS, action_fns; TabKey + navigate_to_tab refactor |
| 5 | P2.1–P2.8 | Model file moves (one per commit); shims left in place |
| 6 | P2.9–P2.15 | Agent + view-model + view moves (one per commit) |
| 7 | P2.16 | MainViewModel decomposition + one-shot rename |
| 8 | P2.17–P2.18 | Fixture move + cleanup commit (remove all shims); ratchet hits zero |
| 9 | P3 | Manifest-driven dispatcher; selector gating; CORELLI tab 5 |
| 10 | P3a | EIC decomposition; EICRowBuilder protocol; SC row builder |
| 11 | P4 | SANS technique skeleton (manifest, models, view-models, views, prompts) |
| 12 | P5 | USANS beamline plug-in |
| 13 | P6 | Docs + acceptance check |

Sessions 5-8 (P2) are the highest-risk because of churn volume. The
one-file-per-commit shim policy keeps mid-session rollback cheap.

## End-state acceptance check

When P6 lands:

1. ✅ `grep -rn 'crystalsystem\|point_group\|centering\|UB\|HKL\|MNP\|peak_radius\|max_q\|d_min\|d_max\|angle_plan\|temporal_analysis\|gonio' src/exphub/app/ src/exphub/core/` returns 0 results
2. ✅ Repo ships `techniques/single_crystal/` + `techniques/sans/`
3. ✅ Repo ships `beamlines/topaz/`, `beamlines/corelli/`, `beamlines/usans/`
4. ✅ Adding a 4th technique family = drop a `techniques/<id>/` folder; no
   framework edits
5. ✅ Adding a 5th beamline of an existing technique = drop a
   `beamlines/<id>/` folder; no framework edits
6. ✅ `BeamlineSpec` is technique-discriminated; `mypy --strict` clean
7. ✅ Cross-technique selector option grayed-out with banner
8. ✅ Agent reads PhaseManager phases, BRIDGED_SUBMODELS, action_fns,
   prompt context, knowledge dir, all from the active manifest
9. ✅ `MainApp()` constructs with `set_active("usans")` from a clean env
10. ✅ All tests green; technique-coupling ratchet at zero;
    beamline-coupling ratchet at zero
