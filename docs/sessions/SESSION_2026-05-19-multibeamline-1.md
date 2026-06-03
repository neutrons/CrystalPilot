# Session 2026-05-19: Multi-Beamline Refactor + UI Wiring

Branch: `multibeamline` (off `agentize`).
Total commits this session: **23**.
Tests: **77 → 83** all green at every commit.
Hardcoded coupling: **235 TOPAZ/BL12 occurrences in 17 files → 0** outside the
allow-list (beamline plug-in dirs + two vendored/docstring exceptions).

## Objective

Take CrystalPilot from a TOPAZ-only deployment to a beamline-agnostic *hub*:
add a new beamline by dropping a directory under `src/exphub/beamlines/<id>/`,
no framework edits required. Tab shell stays put; tab contents, PVs, paths,
agent prompts, and presets all become beamline-pluggable. Then wire a runtime
selector and tighten the Live Data tab's vertical layout.

## Background

The pre-session codebase had TOPAZ/BL12 strings sprinkled across 17 files
including 78 in `views/css_status.py`, 25 in `views/main_view.py`, and
double-digit counts in five Pydantic models. Two `view_models/main.py` had
become a 1626-line god-file. Latent multi-instrument awareness existed in
three places — `agent/constants.py:EXPERIMENT_PRESETS`,
`experiment_info.instrument_list`, `eiccontrol.beamline_database` — but
nothing dispatched off them.

The session also covers two follow-up UI tasks: wiring a runtime beamline
selector in the top tab bar, and rebalancing the Live Data Processing tab
so the figures get the dominant vertical share over the UB/lattice/beam
strip. A blank-page regression introduced by the first selector commit was
diagnosed and fixed.

## Approach Evaluated

Three architectural options were considered for multi-beamline support:

- **A: BeamlineSpec + Registry plug-in** (chosen) — one Pydantic model that
  every beamline populates; framework code reads from `BeamlineContext`
  rather than literal constants. Adding a beamline = adding a folder.
- **B: Per-beamline model subclasses** — `TopazExperimentInfoModel(BaseModel)`
  etc. Rejected: combinatorial explosion when beamlines share most fields
  but each tweaks a few.
- **C: Runtime env-var switch** — set `EXPHUB_BEAMLINE=topaz` and have every
  call site read from `os.environ`. Rejected: scatters lookups everywhere
  and provides no schema for what each beamline must declare.

A was selected because it (1) gives one authoritative contract,
(2) lets the registry auto-discover plug-in folders, and (3) keeps
TOPAZ-specific values isolated to `beamlines/topaz/` so future-beamline
work is purely additive.

The plan was written first (`MULTI_BEAMLINE_PLAN.md`, 14 sections + two
appendices) and then executed phase by phase, each phase mergeable on its
own without breaking the TOPAZ deployment.

---

## Implementation — Phases 0–6

### Phase 0 — Guardrails & quick wins (3 commits)

#### `8d29ec3` — land multi-beamline plan; archive session notes

- Wrote `MULTI_BEAMLINE_PLAN.md` (top-level): goals, target architecture,
  `BeamlineSpec` contract, registry + context + switching, tab plug-ins,
  schema overlay strategy, agent multi-beamline/multi-task design, PV
  catalog & path resolver, god-file decomposition, git strategy, phased
  roadmap, risks, open questions, quick wins, acceptance criteria,
  file-by-file migration cheat sheet.
- Moved 9 stale `SESSION_*.md` files from repo root to `docs/sessions/`.
- Moved stale `CODEBASE_REPORT.md` (2026-03-30) to `docs/archive/`.
- Carried over the untracked `CLAUDE.md` (project instructions) into the
  branch.

#### `e208765` — add beamline-coupling regression ratchet

- New `tests/test_beamline_coupling.py` — three tests:
  - `test_no_unrecorded_coupling_sites` — fails if a new file picks up
    `TOPAZ|BL12` outside allow-list.
  - `test_coupling_does_not_regress` — per-file upper bound (acts as a
    ratchet that gets tightened each phase).
  - `test_total_coupling_count` — total stays ≤ recorded baseline.
- Initial baseline: 235 occurrences (re.findall counts) across 17 files.
- The ratchet replaces lint-style enforcement with a soft regression net
  that documents progress and fails any phase that backslides.

#### `d9eacf5` — move 47 point-group angle lists from main.py to JSON fixture

- `view_models/main.py:580–1374` had a 1000-line cascade of `if
  point_group == "X": final_angle_list = [...]` for 47 point groups —
  development-time fixtures.
- AST-extracted each list, wrote to
  `src/exphub/app/fixtures/optimizer_fallback_angles.json` (31 KB).
- Replaced the cascade with a 7-line `_load_optimizer_fallback_angles()`
  helper using `@lru_cache` for a single JSON read.
- `view_models/main.py`: **1626 → 860 lines** (−766).
- Verified data parity: m-3m's 5 rows preserved, point-group "1"'s 202
  rows starting `[138.0, 135, 80.0]`.

### Phase 1 — Beamline plug-in foundation (4 commits)

#### `e843901` — add `core/beamline` package (Spec, Registry, Context)

New package `src/exphub/core/beamline/`:

- **`spec.py`** — Pydantic data classes:
  - `GoniometerSpec` (type, angle_pvs, ramp_pvs, charge_pv, angle_columns_order)
  - `DetectorSpec` (bob_screen_path, macros_path, extra_subscribe_pvs,
    detector_layout, pixel_dims)
  - `MantidSpec` (instrument_name, wavelength_min/max, default_max_q,
    default_tolerance, default_num_peaks_to_find)
  - `PathsSpec` (shared_root, eic_dropbox, default_calibration,
    autoreduce_subdir, live_monitor_subdir)
  - `EICSpec` (beamline_code, is_simulation_default, write_scope)
  - `AgentSpec` (context_prompt, knowledge_dir, presets, supported_tasks)
  - `TabOverrides` (per-tab plug-in points)
  - `BeamlineSpec` (id, display_name, facility, target_station,
    package_path, all the above subspecs) + `resolve(relative)` for
    path resolution against the plug-in package root.

- **`registry.py`** — module-level registry surface:
  - `register(spec)` — idempotent; auto-resolves `package_path` from
    caller's `inspect.stack()` frame.
  - `get(id)`, `list_ids()` — lazy `_discover()` triggers
    `importlib.import_module("exphub.beamlines")`.
  - `set_active(id)` / `active()` — tracks active beamline; `active()`
    falls back to first-registered when nothing has been set.
  - `_reset_for_tests()` helper.

- **`context.py`** — `BeamlineContext`: thin facade over a `BeamlineSpec`
  with convenience accessors:
  - PV lookups: `angle_pv(axis)`, `ramp_pv(key)`, `charge_pv`,
    `angle_columns`, `angle_axis_keys`
  - Path builders: `ipts_root(ipts)`, `autoreduce_dir(ipts)`,
    `live_monitor_dir(ipts)`, `eic_dropbox_dir(ipts)`
  - Files: `bob_screen`, `bob_macros`, `extra_subscribe_pvs`

- **`__init__.py`** — public API re-exports.

#### `07ce67d` — add TOPAZ beamline plug-in with spec values

New `src/exphub/beamlines/topaz/`:

- `__init__.py` — imports `.spec` so `register(TOPAZ)` fires on import.
- `spec.py` — `TOPAZ = BeamlineSpec(...)` populated with values
  consolidated from the pre-refactor codebase:
  - 19-PV `TOPAZ_USER_PANEL_PVS` tuple (was `_USER_PANEL_PVS` in `main_view.py`)
  - Goniometer: omega/phi at `BL12:Mot:goniokm:*`, ramp at `BL12:SE:Ramp:*`,
    charge at `BL12:Det:PCharge:C`
  - Mantid: `TOPAZ` instrument, 0.4–3.45 Å, max_q 17.0, tolerance 0.12, 500 peaks
  - Paths: `/SNS/TOPAZ`, `/SNS/groups/topaz/bl_12`, default cal `2026A_CG`
  - EIC: `bl12`
  - Agent: `topaz_standard` preset (moved from `agent/constants.py`)

- `beamlines/__init__.py` — imports `topaz` to trigger registration.
- Coupling test updated: the `src/exphub/beamlines/` prefix is added to
  `ALLOWED_PREFIXES`; `src/exphub/core/beamline/spec.py` (docstring
  example) added to `ALLOWED_FILES`.

#### `e6f6a86` — main_view: load BOB screen + extra PVs from beamline context

- Moved `BL12_ADnED_2D_4x4.bob` and `BL12_ADnED_2D_4x4.macros` from repo
  root to `beamlines/topaz/screens/`.
- `app/views/main_view.py`:
  - Imports `exphub.beamlines` to trigger registration.
  - Stores `self.beamline_ctx = BeamlineContext(active())` on init.
  - `epics.connect(...)` reads `ctx.bob_screen` / `ctx.bob_macros`.
  - `_subscribe_extra_pvs(ctx.extra_subscribe_pvs)` replaces the hardcoded
    19-tuple.
  - Old `_USER_PANEL_PVS` constant deleted.
- **`main_view.py` coupling: 25 → 0.**

#### `b7b1acd` — gonio_pvs: turn into shim re-exporting active beamline's gonio

- New `beamlines/topaz/gonio.py` — owns the literal TOPAZ goniometer/ramp
  PV strings (`AMBIENT`, `CRYOGENIC`, `ANGLE_PVS`, `RAMP_PVS`,
  `RAMP_PV_ALIASES`, `WAIT_FOR_PCHARGE_PV` + 5 helper functions).
- `app/models/gonio_pvs.py` is now a 50-line shim that dynamically
  imports `exphub.beamlines.{active().id}.gonio` and re-exports every
  symbol. Existing callers (`models/angle_plan.py`, `models/eic_control.py`)
  work unchanged.
- **`gonio_pvs.py` coupling: 16 → 0.**
- Phase 1 plan-update commit `3d659a4` recorded the running tally
  (coupling 235 → 194).

### Phase 2 — Path resolver + per-model migration (6 commits)

#### `ec67f68` — add `core/paths` PathResolver

New `src/exphub/core/paths/`:

- `ipts_name(ipts)` — canonical `IPTS-<N>` (idempotent).
- `PathResolver(ctx, ipts)` — properties: `shared_root`,
  `eic_dropbox_root`, `default_calibration`, `ipts_dir`,
  `autoreduce_dir`, `live_monitor_dir`, `eic_dropbox`, plus an
  `ensure_dir(path)` convenience.
- `resolver_for(ipts, beamline_id=None)` — module-level factory.
- Unbound resolver raises `ValueError` with a helpful message if a path
  needing IPTS is accessed without it.

#### `f0ecb93` — temporal_analysis: route paths through PathResolver

`app/models/temporal_analysis.py` migration:

- All `/SNS/TOPAZ/IPTS-{ipts}/...` literals replaced with
  `resolver_for(self.ipts).<property>`.
- `live_topaz-` filename prefix → `live_<active().id>-ipts-` so refined-UB
  files now namespace per beamline.
- `Instrument="TOPAZ"` in Mantid's `StartLiveData` → reads
  `_active_beamline().mantid.instrument_name`.
- Error message "Another MonitorLiveData thread for TOPAZ run %s"
  becomes "for %s run %s" using the instrument name.
- Stale dead-code commented blocks generalised (e.g.
  `/SNS/TOPAZ/IPTS-33641/...` → `/SNS/<instrument>/IPTS-<n>/...`).
- **`temporal_analysis.py` coupling: 19 → 0.**

#### `b9ff0f5` — experiment_info: defaults from active beamline

`app/models/experiment_info.py`:

- New helpers `_default_instrument_list`, `_default_instrument`,
  `_default_cal_filename`, `_default_spectra_filename` — all read from
  `_active_beamline()` with a graceful `""` fallback.
- `Options.instrument_list`: hardcoded `["TOPAZ","MANDI","CORELLI"]` →
  `default_factory=_default_instrument_list` (walks the registry).
- `ExperimentInfoModel.instrument`: `default="TOPAZ"` →
  `default_factory=_default_instrument`.
- `cal_filename`, `spectra_filename`: hardcoded `/SNS/TOPAZ/...` paths →
  factories reading `spec.paths.default_calibration` /
  `spec.paths.default_spectra`.
- `copy_config_files` and `prepare_config_file` use
  `_resolver_for(self.ipts_number).autoreduce_dir`.
- `export_folder = ...ipts_dir + "/shared/ndip/" + exp_name`.
- New `PathsSpec.default_spectra` field; TOPAZ spec populated.
- **`experiment_info.py` coupling: 11 → 0.**

#### `16da40b` — eic_control: route beamline code, run-title PV, dropbox path

`app/models/eic_control.py`:

- New helpers `_default_beamline_code` (reads
  `spec.eic.beamline_code`) and `_default_beamline_database` (walks the
  registry to build `{instrument_name: eic_code}` map).
- `EICControlModel.beamline`: `default="bl12"` →
  `default_factory=_default_beamline_code`.
- `beamline_database`: hardcoded `{"TOPAZ":"bl12","CORELLI":"bl9"}` →
  `default_factory=_default_beamline_database`.
- `_copy_strategy_to_eic`: `destination_dir = "/SNS/groups/topaz/bl_12/..."`
  → `_resolver_for(ipts_number).eic_dropbox`.
- CSV `RunTitle` column: literal `"BL12:SMS:RunInfo:RunTitle"` →
  `_active_beamline().eic.run_title_pv`.
- `submit_eic`'s "is supported beamline" check: `self.beamline != "bl12"`
  → "instrument isn't registered" check via the dynamic database.
- New `EICSpec.run_title_pv` field; TOPAZ spec populated.
- **`eic_control.py` coupling: 8 → 0.**

#### `a2ad830` — angle_plan: instrument + placeholder row + run-title PV

`app/models/angle_plan.py`:

- `_default_instrument_name` factory replaces hardcoded `"TOPAZ"`.
- `_default_angle_list_read` factory builds the placeholder row using
  the active beamline's goniometer PV names (was hardcoded
  `"BL12:Mot:goniokm:phi"` / `:omega`).
- CSV writer `export_to_nxv_csv` uses
  `_active_beamline().eic.run_title_pv` instead of the BL12 literal.
- Dead commented `#` blocks with BL12 motor names stripped.
- **`angle_plan.py` coupling: 9 → 0.**

#### `c00b9a4` — data_analysis + view stragglers

- `models/data_analysis.py`: 7 hardcoded `/SNS/TOPAZ/IPTS-12132/...`
  placeholder defaults → empty strings (user populates).
- `views/data_analysis.py`: hardcoded `nova.ornl.gov` data-reduction URL
  → reads `_active_beamline().external_links["data_reduction"]`. New
  `BeamlineSpec.external_links: dict[str,str]` field; TOPAZ spec
  populated.
- `views/temporal_analysis.py`: hardcoded `BL12:Det:PCharge:C` and
  `BL12:Det:rtdl:BeamPowerAvg` PVInputs → read
  `_active_beamline().detector.monitor_pvs.get("proton_charge"/...)`.
  New `DetectorSpec.monitor_pvs: dict[str,str]` field; TOPAZ spec
  populated (proton_charge, beam_power, wavelength).
- `app/main.py`: comment "The TOPAZ 2D detector PV (1105-wide heatmap)"
  generalised to "Large 2D detector PVs (e.g. a 1105×1105 heatmap)".
- `view_models/main.py` + `view_models/angle_plan.py`: dead commented
  blocks with `BL12:Mot:goniokm:...` motor lookups stripped.
- `eic_client.py` allow-listed (vendored EIC client carries a
  name-normalizer table for every SNS beamline — too coupled to a
  generic SNS layout to migrate).
- Phase 2 plan-update commit `55f1622` (coupling 194 → 121, app side at 0).

### Phase 4 — Tab plug-in (1 commit)

#### `6780062` — css_status: move to beamlines/topaz/tabs

- Moved `src/exphub/app/views/css_status.py` (414 lines, 115 TOPAZ/BL12
  refs — the full ADnED 4×4 panel) wholesale to
  `src/exphub/beamlines/topaz/tabs/css_status.py`.
- Fixed the relative import: `from ..view_models.main` →
  `from ....app.view_models.main`.
- `BeamlineSpec.TabOverrides` field type relaxed from `Callable[..., Any]`
  to `Any` so a view class or a factory function both work.
- TOPAZ spec adds `tabs=TabOverrides(css_status=_build_css_status)` where
  `_build_css_status(view_model)` is a **lazy-import factory** — eager
  import would trigger a cycle through the `gonio_pvs` shim (which
  resolves the active beamline at import time).
- `app/views/tab_content_panel.py` deletes its `from .css_status import
  CSSStatusView`; tab 5 now reads
  `_active_beamline().tabs.css_status(view_model)` with a graceful
  "not configured for this beamline" placeholder fallback.
- **`css_status.py` coupling: 115 → 0** (the file moved into an
  allow-listed dir; the strings inside it are now legitimate TOPAZ data).

### Phase 5 — Agent multi-beamline / multi-task (2 commits)

#### `d82b265` — agent: presets aggregated from registry

`agent/constants.py`:

- Deleted the hardcoded `EXPERIMENT_PRESETS` dict (had topaz_standard,
  corelli_standard, mandi_standard).
- Replaced with `get_experiment_presets()` that walks the registry and
  unions `spec.agent.presets` from every registered beamline.

`agent/tools.py`:
- `apply_preset` and `list_presets` use `get_experiment_presets()`.

`agent/handlers.py`:
- `handle_list_presets` uses the live registry; example preset shown in
  the reply is `next(iter(presets))` (first registered) rather than the
  hardcoded `topaz_standard`.
- `handle_help_request` text "Apply presets: say *apply topaz_standard*
  (or corelli/mandi)" → dynamically lists registered preset names with
  graceful fallback when none are registered.

`agent/rag.py`:
- Docstring example "what is the TOPAZ wavelength range" → "what is the
  wavelength range".

**Agent coupling: `constants.py` 2, `handlers.py` 2, `rag.py` 2 → 0/0/0.**

#### `fd29d4d` — agent: prompt composer

New files:

- `agent/prompts/composer.py` — `compose_system_prompt(beamline_id, task)`
  assembles the system prompt from three fragments:
  1. `core_identity.md` (beamline-agnostic identity, workflow phases,
     job-selection grammar — the bulk of the original `system_prompt.md`)
  2. `<beamline_pkg>/prompts/context.md` (per-beamline intro)
  3. `tasks/<task>.md` (per-task instructions)

  Falls back to legacy single-file `system_prompt.md` if no fragments
  exist. `describe_active_context(beamline_id, task)` returns a
  one-liner like `ACTIVE_BEAMLINE: TOPAZ (SNS BL-12) [SNS/TS-1] |
  ACTIVE_TASK: experiment_steering` injected into every turn's
  `SystemMessage`.

- `agent/core_aliases.py` — tiny indirection (`active_spec(id)`) that the
  composer uses to avoid an import cycle through `exphub.core.beamline`.

- `agent/prompts/core_identity.md` — beamline-agnostic identity (renamed/
  trimmed from `system_prompt.md`).

- `agent/prompts/tasks/experiment_steering.md` — the first task fragment.

- `beamlines/topaz/prompts/context.md` — TOPAZ instrument intro
  (wavelength band, detector, gonio types, paths, default preset name).

`agent/agent.py`:

- `_load_system_prompt` now delegates to the composer; old module-level
  `SYSTEM_PROMPT` retained for back-compat but the per-instance
  `self.system_prompt` is what `_call_model_node` uses.
- `Agent.__init__` gains `beamline_id` and `task` kwargs; defaults to
  `"experiment_steering"`.
- `_call_model_node` injects `describe_active_context(...)` as a
  `SystemMessage` after the main prompt so every turn carries
  `ACTIVE_BEAMLINE` / `ACTIVE_TASK` info.

- Legacy `prompts/system_prompt.md` deleted.

### Phase 6 — Onboard CORELLI (1 commit)

#### `3bc5f2e` — onboard CORELLI as 2nd beamline plug-in; 8 new tests

This was the **acceptance test** for the abstraction — *zero* framework
edits, only one `import .corelli` line in
`beamlines/__init__.py` for discovery.

New files under `src/exphub/beamlines/corelli/`:

- `__init__.py` — imports `.spec`.
- `spec.py` — `CORELLI = BeamlineSpec(...)` populated with placeholder
  values mirroring TOPAZ's structure (`BL9:Mot:Sample:omega`, etc.).
- `gonio.py` — `BL9:`-prefixed PV definitions; same public surface as
  TOPAZ's gonio module.
- `prompts/context.md` — CORELLI intro (statistical chopper,
  cross-correlation, diffuse-scattering use cases).
- `knowledge/corelli_overview.md` — placeholder for RAG.
- **No `tabs/css_status.py`** yet — tab 5 renders the
  "not configured" placeholder for CORELLI; documented as future work.

Framework changes (one line + one tweak):

- `beamlines/__init__.py` — `from . import corelli` after topaz.
- `core/beamline/registry.py` — `active()` fallback changed from
  *alphabetical* (`sorted(_REGISTRY)[0]`) to *insertion-order*
  (`next(iter(_REGISTRY.values()))`) so the import order in
  `beamlines/__init__.py` dictates the default. Without this CORELLI
  (alphabetically first) would override TOPAZ as default.

New `tests/test_multi_beamline.py` (8 tests):

- `test_both_beamlines_registered`
- `test_topaz_is_default_active`
- `test_set_active_swaps_pvs_and_paths` — verifies omega/phi PVs,
  IPTS/EIC paths swap when active beamline changes.
- `test_set_active_swaps_presets` — `topaz_standard` ↔ `corelli_standard`
  visibility.
- `test_prompt_composer_includes_active_beamline_context` — TOPAZ context
  appears under `set_active("topaz")` but not under
  `set_active("corelli")`, and vice versa; both share `core_identity`.
- `test_describe_active_context` — per-turn line says `TOPAZ` /
  `CORELLI` correctly.
- `test_agent_presets_aggregate_from_registry` — `get_experiment_presets()`
  returns both `topaz_standard` and `corelli_standard`.
- `test_corelli_spec_resolves_paths_relative_to_package` — `bob_screen` is
  `None` (no .bob shipped) without crashing; `context_prompt` resolves
  into the corelli package dir.

Test count: **77 → 85**.

### Final wrap-up (1 commit)

#### `f838e2b` — wrap-up: zero-coupling regression test, onboarding doc, plan status

- `tests/test_beamline_coupling.py` simplified: with every per-file
  baseline at 0, replaced the three ratchet tests (per-file, total,
  no-new-file) with one stricter test
  `test_no_framework_side_beamline_coupling` that asserts `_scan()` is
  empty. Any reintroduction of TOPAZ/BL12 strings outside the allow-list
  fails the test.
- New `docs/adding_a_beamline.md` — step-by-step onboarding guide
  (directory skeleton, what `spec.py` needs, how to wire discovery,
  prompts, knowledge base, optional tab overrides, smoke-check
  snippets, notes on the vendored EIC client edge case).
- `MULTI_BEAMLINE_PLAN.md` updated with the full phase-landing table and
  an Acceptance-check section ticking off Appendix A's 7 criteria.

Final test count: **83** (the three ratchet tests collapsed into one).

---

## Implementation — UI follow-ups (3 commits)

### `a87b57c` — tabs_panel: add beamline selector inline with tab strip

- `view_models/main.py:ViewState` gained three fields:
  - `beamline_id: str = Field(default_factory=_default_beamline_id)`
  - `beamline_options: list[dict] = Field(default_factory=_default_beamline_options)`
  - `beamline_switch_notice: str = Field(default="")`
- `MainViewModel.switch_beamline(beamline_id)` calls
  `set_active(beamline_id)`, updates the view state, posts a notice.
- `views/tabs_panel.py` rebuilt: wraps `VTabs` + `VSelect` in a
  `display:flex` row so they occupy the same vertical band; tabs take
  `flex: 1 1 auto`, selector hugs the right at 160–220 px.
- Snackbar added to surface the post-switch notice.
- **This commit had a bug** — see `556bc7f` below.

### `8bc6ea2` — temporal_analysis: compact UB/lattice/beam-status strip; figures get 4:1 vspace

- Figures wrapped in `html.Div(style="flex: 4 1 0; min-height: 0;
  display: flex; flex-direction: column;")` so the plotly grid claims
  the dominant vertical share.
- UB/lattice/beam-status strip wrapped in
  `html.Div(style="flex: 0 0 auto;")` so it sizes to content and never
  bloats vertically.
- **Left card restructured**: UB matrix and lattice constants used to be
  stacked vertically (UB on top, lattice below). Now they render
  **side-by-side** inside a flex container (`display: flex; gap: 0.75em`),
  cutting the strip's vertical footprint roughly in half.
- Lattice no longer pads a 3×3 grid (V used to sit alone with two empty
  cells); a–c and α–γ render in the 3-column grid, V on a single-line
  caption below.
- Cell-style tightened: padding `4px 10px → 2px 6px`, font
  `0.95em → 0.85em`, `min-width 90 → 70 px`.
- The "UB saved: …" footnote moved from under the lattice card into the
  beam-status card so it doesn't pad the UB area.

### `556bc7f` — fix blank page

**Bug surfaced by user**: after `pixi run app`, browser opened to a
fully blank page.

**Root cause** — the snackbar from `a87b57c` had:
```python
vuetify.VSnackbar(
    v_model=("controls.beamline_switch_notice != ''",),
    update_modelValue=("controls.beamline_switch_notice = ''", "[$event]"),
)
```
Vuetify's `v-model` requires a writable boolean state reference, not a
computed expression. The malformed `update_modelValue` tuple compounded
it. Vue threw at component-registration time → the whole app failed to
mount → blank page.

A second issue: `VSelect.update_modelValue=(callable, "[$event]")` is
not the right way to wire a Python callback to a value-change event in
this codebase — `update_modelValue` accepts a JS string only;
Python callbacks go through binding callbacks or `click=`.

**Fix**:

1. New `ViewState.beamline_switch_visible: bool` field. Snackbar binds
   `v_model="controls.beamline_switch_visible"` (proper boolean state
   ref). `timeout=6000` auto-dismisses.
2. `update_modelValue` removed from the VSelect. Instead,
   `view_state_bind` now carries
   `callback_after_update=self.on_view_state_change` — the standard
   pattern the rest of the codebase uses for VM binding (matches
   `experimentinfo_bind`, `angleplan_bind`).
3. `MainViewModel._last_beamline_id` tracks the last value so the
   callback only fires on genuine user picks, not on our own
   programmatic `_push_view_state()` writes (which would otherwise
   re-enter and loop).
4. `switch_beamline` sets `beamline_switch_visible = True` after
   activating the new spec; the snackbar auto-shows.
5. `tabs_panel.py` simplified to mirror existing working patterns:
   `from trame_client.widgets import html` (matches `main_view.py` and
   `chat_pane.py`), no `update_modelValue` tuples.

**Verification**: `MainApp()` constructs end-to-end without exception;
83 tests still green.

---

## Outcome

### Quantitative

| Metric | Before | After |
|---|---|---|
| Hardcoded TOPAZ/BL12 in framework code | 235 across 17 files | **0** outside `beamlines/` (allow-listed) |
| Beamline plug-ins shipped | 0 (TOPAZ implicit everywhere) | **2** (TOPAZ + CORELLI) |
| Tests | 75 | **83** |
| `view_models/main.py` lines | 1626 | 859 |
| Commits on `multibeamline` branch | 0 | **23** |

### Files touched (summary)

**New files** (under `src/`):
- `core/__init__.py`
- `core/beamline/__init__.py`, `spec.py`, `registry.py`, `context.py`
- `core/paths/__init__.py`, `resolver.py`
- `beamlines/__init__.py`
- `beamlines/topaz/__init__.py`, `spec.py`, `gonio.py`
- `beamlines/topaz/screens/BL12_ADnED_2D_4x4.bob` (moved from repo root)
- `beamlines/topaz/screens/BL12_ADnED_2D_4x4.macros` (moved)
- `beamlines/topaz/tabs/__init__.py`, `css_status.py` (moved from
  `app/views/`)
- `beamlines/topaz/prompts/context.md`
- `beamlines/corelli/__init__.py`, `spec.py`, `gonio.py`
- `beamlines/corelli/prompts/context.md`
- `beamlines/corelli/knowledge/corelli_overview.md`
- `agent/core_aliases.py`
- `agent/prompts/composer.py`
- `agent/prompts/core_identity.md` (renamed from `system_prompt.md`)
- `agent/prompts/tasks/experiment_steering.md`
- `app/fixtures/optimizer_fallback_angles.json`

**New top-level files**:
- `MULTI_BEAMLINE_PLAN.md`
- `docs/adding_a_beamline.md`
- `docs/archive/CODEBASE_REPORT.md` (moved)
- `docs/sessions/SESSION_*.md` (9 files moved)
- `tests/test_multi_beamline.py`
- `tests/test_beamline_coupling.py`

**Modified** (under `src/`):
- `agent/constants.py`, `handlers.py`, `tools.py`, `rag.py`, `agent.py`
- `app/main.py`
- `app/models/data_analysis.py`, `eic_control.py`, `experiment_info.py`,
  `gonio_pvs.py`, `temporal_analysis.py`, `angle_plan.py`
- `app/view_models/main.py`, `angle_plan.py`
- `app/views/main_view.py`, `tab_content_panel.py`, `tabs_panel.py`,
  `temporal_analysis.py`, `data_analysis.py`

**Deleted**:
- `BL12_ADnED_2D_4x4.bob` (moved into TOPAZ plug-in)
- `BL12_ADnED_2D_4x4.macros` (moved)
- `agent/prompts/system_prompt.md` (split into core_identity + per-beamline
  context + per-task fragments)
- `app/views/css_status.py` (moved into TOPAZ plug-in)
- 9 stale `SESSION_*.md` and `CODEBASE_REPORT.md` (moved to docs)

### Acceptance check (against MULTI_BEAMLINE_PLAN.md Appendix A)

1. ✅ `grep -r "TOPAZ|BL12" src/` returns 0 results outside
   `beamlines/<id>/` and `tests/` (vendored `eic_client.py` and one
   docstring in `core/beamline/spec.py` are explicit allow-list exceptions).
2. ✅ Repo ships **TOPAZ + CORELLI** plug-ins.
3. ✅ A new beamline is added by editing only files under
   `beamlines/<new_id>/` (CORELLI was added with one new directory; the
   only framework-side line edited was an `import .corelli` in
   `beamlines/__init__.py` for discovery).
4. ✅ Agent system prompt is composed at runtime from
   `(core_identity + beamline_context + task)`; tested for both
   beamlines.
5. ✅ **Runtime switching works** — `set_active(...)` swaps
   PVs/paths/presets/prompt. The toolbar selector wires this end-to-end
   for the user.
6. ✅ All 83 tests pass.
7. ✅ `docs/adding_a_beamline.md` exists.

---

## What's left

- **Hot-swap completeness**. The selector activates a new spec in the
  registry and pushes a snackbar, but:
  - `epics.connect(.bob)` happens once at `MainApp.__init__`. The
    Instrument Status (CSS) tab can't hot-swap mid-session.
  - Pydantic `default_factory` resolves on instance construction; existing
    model instances keep their initial defaults. Field-level mutation
    via the GUI works as normal; only the *implicit defaults* don't
    re-roll.
  - Agent's RAG index is per-process; switching reloads the prompt but
    not the ChromaDB collection until next launch.

  The snackbar message tells the user a restart is required for the
  affected paths. A proper hot-swap would need to re-do
  `MainApp._subscribe_extra_pvs`, re-init the ChromaDB collection, and
  decide a policy for stale model-field defaults.

- **CORELLI tab 5 placeholder**. CORELLI has no
  `beamlines/corelli/tabs/css_status.py`, so the Instrument Status tab
  renders the "not configured for this beamline" `VAlert` placeholder.
  Adding one is a clean-room task — get the BL-9 `.bob` screen, write
  the layout, point `TabOverrides.css_status` at a lazy factory.

- **Other tabs as plug-ins**. Only `css_status` is currently overridable
  per beamline. The other four tabs (experiment_info, angle_plan,
  temporal_analysis, data_analysis) use shared models that already pull
  per-beamline values from the spec, so they don't *need* tab overrides
  — but the `TabOverrides` field exists for them if a beamline's needs
  diverge.

- **`view_models/main.py` god-file decomposition** (Phase 3 in the
  original plan) was deferred. The file is down to 859 lines from 1626,
  and zero coupling, so it's no longer blocking. Splitting per-tab VMs
  into separate files is still good hygiene.

- **`eic_client.py` decomposition** (1566 lines). Listed in the plan,
  deferred as out of scope; the file is allow-listed.

- **Task-aware tool filtering**. The plan describes
  `TaskId = Literal["experiment_steering", "data_processing", ...]`
  with per-task tool subsets. Phase 5 added the prompt fragment dimension
  but not the tool filter. A new `core/tasks/registry.py` is the natural
  home for `{task: [tool_names]}`.

- **Beamline selector UX polish**. The current dropdown sits at the same
  height as the tab labels but doesn't have a visible separator or
  facility/station subtext. The post-switch snackbar is honest about
  the restart requirement; integrating a one-click "restart now" would
  be helpful when the user just wants to fully switch.
