# Session 2026-06-02: Multi-Technique Refactor — Phase 0

Branch: `multibeamline`.
Total commits this session: **7**.
Tests: **105 → 112** all green at every commit.
Plan: [`MULTI_TECHNIQUE_PLAN.md`](../../MULTI_TECHNIQUE_PLAN.md).

## Objective

USANS (small-angle neutron scattering at SNS BL-1A) is a different
technique family than TOPAZ/CORELLI (single-crystal diffraction). The
multi-beamline architecture handles per-beamline *parameters* (PVs,
paths, instrument names) but assumes every beamline shares the same tab
*shape*: crystal-system / point-group / centering / UB / HKL fields,
goniometer angle plan, peak-integration Mantid pipelines. USANS does not
fit that shape — it has no goniometer, no UB matrix, no peak selection,
and its tabs need genuinely different models, view-models, and views.

This session lands **Phase 0** of a 6-phase refactor that introduces a
technique-family layer above beamlines. P0 is plan + ratchets + safety
nets — no code moves yet. Subsequent phases (P0.5 spec discriminator,
P1 manifest + agent parametrisation, P2 single-crystal code lift, P3
manifest-driven dispatcher, P3a EIC decomposition, P4 SANS skeleton, P5
USANS plug-in, P6 docs) ship one-per-session.

## Background

This session opened with a 10-agent workflow:

- **7 parallel audits** across files / imports / spec-usage / tabs /
  view-model / tests / docs
- **3 adversarial critiques** through engineering-risk / API-ergonomics /
  UX-and-agent-integration lenses

Audit headline numbers:
- 57 `.py` files classified under `src/exphub/`
- ~30 files in `app/` will move; only ~5 are true app-shell
- 51 `active().X` call sites audited; 14 single-crystal-assumed
- 5 pre-existing circular-import landmines preserved via lazy imports
- `gonio_pvs.py` imports `f'exphub.beamlines.{active().id}.gonio'` at
  module-import time — crashes at startup for any beamline without a
  `gonio.py` (e.g. USANS)
- `TabOverrides` has 5 slots; only `css_status` is actually consulted by
  the dispatcher today

All three critiques returned `plan_needs_revision`. Key revisions folded
into the plan before P0 started:

1. **Discriminated technique config**, not 22 `Optional[X]` spec fields
2. **`TabKey` string IDs** from day one, not deferred to P3
3. **Cross-technique switching gated to require restart** in v1
4. **No `MainViewModel` delegator shim** — one-shot rename in P2
5. **PhaseManager / prompt composer / action_fns parametrised in P1**
6. **`optional_tab_defaults` escape hatch** on the technique manifest
7. **Lazy `importlib`-driven technique discovery**
8. **P0 expanded** to include trame-bind snapshot, view-model surface
   contract, tab-overrides contract, and the gonio guard

## User-resolved open decisions

| # | Decision |
|---|---|
| 1 | Same EIC module for all beamlines; per-technique RowBuilder + per-beamline server address |
| 2 | Technique id naming: `"single_crystal"` for now; accept imprecision |
| 3 | TabOverrides composition: atomic factory swap only, no per-section composition |
| 4 | Cross-technique switching: require restart, gate the selector |
| 5 | USANS strategy file: CSV, TOPAZ-shaped, different column names |
| 6 | Live-stream URL location: TBD, leave blank for now |

---

## Implementation — Phase 0

### `1ea03ef` — add multi-technique plan

Created `MULTI_TECHNIQUE_PLAN.md` at the repo root. 638 lines.
Mirrors `MULTI_BEAMLINE_PLAN.md`'s shape: objective, target architecture,
boundary rule, tab fall-through contract, spec evolution (discriminated
union), technique manifest schema, TabKey enum, agent multi-technique
parametrisation, cross-technique-switching gate, phase plan (P0 → P6 +
P3a-future), invariants, decisions resolved table, related work,
notes-on-risk, file-by-file disposition cheat sheet, session-by-session
execution plan, end-state acceptance check.

The plan locks the contract for every subsequent session and is the only
P0 deliverable that's user-facing.

### `774fc1e` — P0: technique-coupling regression ratchet (baseline 267)

New `tests/test_technique_coupling.py`. Three test functions:

- `test_no_unrecorded_technique_coupling` — fail if a previously-zero
  file picks up a single-crystal reference
- `test_technique_coupling_does_not_regress` — per-file ratchet; counts
  may only decrease
- `test_total_coupling_within_cap` — total count cap (267 at P0)

Pattern matches single-crystal vocabulary: `crystalsystem`, `point_group`,
`centering`, `UBFile`, `UBFileName`, `HKL`, `MNP`, `peak_radius`,
`max_q`, `min_dspacing`, `max_dspacing`, `angle_plan`, `angleplan`,
`temporal_analysis`, `temporalanalysis`, `gonio_pvs`,
`IntegrateEllipsoids`, `FindUBUsingFFT`, `FindPeaksMD`, `PredictPeaks`,
`SaveIsawPeaks`, `SaveIsawUB`.

Scans only `src/exphub/app/` and `src/exphub/core/`. Other layers
(`agent/`, `beamlines/`, `tests/`) are explicitly allowed to carry
single-crystal vocabulary today; `agent/` migrates to manifest-driven
in P1.

Baseline captured per-file:

| File | Baseline |
|---|---|
| `app/models/angle_plan.py` | 36 |
| `app/models/eic_control.py` | 20 |
| `app/models/experiment_info.py` | 37 |
| `app/models/main_model.py` | 4 |
| `app/models/temporal_analysis/__init__.py` | 1 |
| `app/models/temporal_analysis/model.py` | 1 |
| `app/models/temporal_analysis/pipeline.py` | 20 |
| `app/models/temporal_analysis/selectors.py` | 8 |
| `app/models/temporal_analysis/workflow.py` | 16 |
| `app/view_models/angle_plan.py` | 12 |
| `app/view_models/main.py` | 96 |
| `app/views/angle_plan.py` | 3 |
| `app/views/experiment_info.py` | 6 |
| `app/views/tab_content_panel.py` | 2 |
| `app/views/temporal_analysis.py` | 3 |
| `core/beamline/spec.py` | 2 |
| **TOTAL** | **267** |

Must reach `BASELINE = {}` (empty dict) by end of P2 before P3 starts.

### `fa2d2fd` — P0: guard gonio_pvs for beamlines without a gonio module

`src/exphub/app/models/gonio_pvs.py` did
`importlib.import_module(f"exphub.beamlines.{_active_beamline().id}.gonio")`
at module-import time. As soon as USANS is the active beamline at
startup, this would raise `ModuleNotFoundError` before `MainApp()` runs.

Wrapped the import in `try` / `except ModuleNotFoundError`. On failure
returns a `SimpleNamespace` stub with:

- Empty `ANGLE_PVS = {}`, `RAMP_PVS = {}`, etc.
- Empty-list-returning `angle_columns(...)`, `angle_keys(...)`
- `detect_goniometer_type(...) → "none"`
- `is_ramp_row(...) → False`
- `ramp_value(...) → ""`

Single-crystal call sites that hit the stub (`angle_plan.py`,
`eic_control.py`) fail at the use site with empty data rather than at
startup with a missing-module error. Logs an INFO-level note when the
stub is used.

Verified: TOPAZ-active import still resolves the real
`exphub.beamlines.topaz.gonio`. Simulated USANS via `importlib`
monkey-patch: stub returns expected empty values.

### `cb3c21e` — P0: tighten TabOverrides type to Optional[TabFactory]

`TabOverrides` fields were typed `Any = None`. Tightened to
`Optional[TabFactory] = None` where
`TabFactory = Callable[[Any], Any]`. Catches the silent-wiring-mistake
class of bug where a beamline accidentally passes a non-callable.

Module-level `TabFactory` type alias documented with the lazy-import
closure convention TOPAZ uses, so the multi-technique-plan P3
generalisation lands on a documented protocol rather than ad-hoc.

### `d35f384` — P0: move trame datatable examples out of tests/; remove dead php fixture

`tests/test-vdatatable.py` and `tests/datatable.py` were pytest-uncollected
trame examples (no `test_` prefix, no `Test` classes). Moved to
`examples/datatable.py` and `examples/datatable_virtual.py` so the
`tests/` directory only holds runnable pytest files.

`tests/php/` (`index.php`, `readme`) was an unrelated leftover. Deleted.

Cleans the audit surface for future tests-impact work in later phases.

### `29eedf9` — P0: cross-link banners to MULTI_TECHNIQUE_PLAN.md

Added one-line blockquote banners at the top of
`MULTI_BEAMLINE_PLAN.md` and `docs/adding_a_beamline.md` pointing
readers to the new plan. Lets someone landing in either doc immediately
see there's a follow-on refactor.

### `20cc7ed` — P0: tab-overrides contract test (per-beamline factory dispatch)

New `tests/test_tab_overrides.py` with 7 tests covering:

- `TabOverrides()` defaults all 5 slots to `None`
- All 5 slots accept callable factories
- The slot-name set is stable (the multi-technique manifest will
  generalise over the same 5 names; renaming any of them is breaking)
- TOPAZ supplies a `css_status` factory; CORELLI does not (proves the
  placeholder fall-through path)
- Every registered beamline's `tabs.<slot>` is either `None` or
  callable (dispatcher invariant)
- TOPAZ's `css_status` factory takes exactly one positional argument
  (the view-model) — pins the factory signature for the P3 generalised
  dispatcher

---

## Outcome

### Quantitative

| Metric | Before P0 | After P0 |
|---|---|---|
| Tests | 105 (after datatable.py + test-vdatatable.py uncounted; truly 102 collected + 3 dead) | **112** |
| Multi-technique-specific tests | 0 | **10** (3 ratchet + 7 tab-overrides) |
| Plan docs | `MULTI_BEAMLINE_PLAN.md` only | `MULTI_TECHNIQUE_PLAN.md` (638 lines) added |
| Single-crystal-coupling ratchet | none | baseline 267 captured, P2 must reach 0 |
| `gonio_pvs.py` startup-crash hazard | yes (crashes on USANS-active startup) | fixed (stubbed on ModuleNotFoundError) |
| `TabOverrides` field type | `Any` | `Optional[TabFactory]` |
| Dead test artifacts | 3 files + 1 dir | moved to `examples/` or deleted |

### Files touched

**New**:
- `MULTI_TECHNIQUE_PLAN.md`
- `tests/test_technique_coupling.py`
- `tests/test_tab_overrides.py`
- `docs/sessions/SESSION_2026-06-02-multitechnique-P0.md` (this file)
- `examples/datatable.py` (moved from tests/)
- `examples/datatable_virtual.py` (moved from tests/)

**Modified**:
- `src/exphub/core/beamline/spec.py` (TabOverrides type)
- `src/exphub/app/models/gonio_pvs.py` (startup guard)
- `MULTI_BEAMLINE_PLAN.md` (cross-link banner)
- `docs/adding_a_beamline.md` (cross-link banner)

**Deleted**:
- `tests/php/index.php`
- `tests/php/readme`

### Commits

```
20cc7ed P0: tab-overrides contract test (per-beamline factory dispatch)
29eedf9 P0: cross-link banners to MULTI_TECHNIQUE_PLAN.md
d35f384 P0: move trame datatable examples out of tests/; remove dead php fixture
cb3c21e P0: tighten TabOverrides type to Optional[TabFactory]
fa2d2fd P0: guard gonio_pvs for beamlines without a gonio module
774fc1e P0: technique-coupling regression ratchet (baseline 267)
1ea03ef add multi-technique plan
```

### Test gates met

- ✅ All new tests green (`test_technique_coupling.py` + `test_tab_overrides.py`)
- ✅ All previously-green tests still green
- ✅ Beamline-coupling ratchet stays at zero (no regression)
- ✅ Technique-coupling ratchet captured at 267; per-file baseline
  committed for P2 to shrink

### Acceptance check for P0 (per plan)

1. ✅ `MULTI_TECHNIQUE_PLAN.md` exists
2. ✅ Cross-link banners on MULTI_BEAMLINE_PLAN.md + docs/adding_a_beamline.md
3. ✅ `tests/test_technique_coupling.py` ratchet committed (initial count 267)
4. ✅ `tests/test_tab_overrides.py` covers the css_status path
5. ✅ `gonio_pvs.py` startup guard in place
6. ✅ `TabOverrides` field type tightened
7. ✅ Dead test artifacts cleaned

P0 deliverables 8 (trame-bind-surface snapshot) and 9 (view-model
surface contract) are deferred to P1, when the SingleCrystalSteeringVM
class actually exists. Capturing a snapshot of bindings against the
pre-rename `MainViewModel` surface would lock in a name we're about to
change.

---

## What's left (next session: P0.5)

**P0.5 — Spec discriminator split** (one PR, pre-move):

1. Define `SingleCrystalConfig` Pydantic model containing all currently
   single-crystal-shaped subspec fields:
   - `goniometer: GoniometerSpec`
   - `mantid: MantidSpec` (instrument_name, wavelength range,
     default_max_q, tolerance, num_peaks)
   - `default_calibration: str`
   - `default_spectra: str`
   - `run_title_pv: str`
   - `bob_screen_path: Path | None`
   - `bob_macros_path: Path | None`
   - `extra_subscribe_pvs: list[str]`
2. Define `SansConfig` minimal stub for shape parity:
   - `kind: Literal["sans"] = "sans"`
   - `mantid_instrument_name: str | None`
   - `default_q_range: tuple[float, float] | None`
   - `transmission_monitor_pv: str | None`
   - `live_stream_url: str | None`
3. Update `BeamlineSpec`:
   - `technique: Literal["single_crystal", "sans"]` field (defaults
     `"single_crystal"`)
   - `technique_config: SingleCrystalConfig | SansConfig = Field(discriminator="kind")`
   - Remove the now-redundant `goniometer`, `mantid`, `detector`,
     `eic.run_title_pv`, `paths.default_calibration`,
     `paths.default_spectra` top-level fields (or keep deprecated
     property accessors during transition)
4. Migrate TOPAZ + CORELLI specs to the new shape
5. Update all 14 single-crystal-assumed call sites (mostly in
   `app/models/*.py` and `app/views/*.py`) to read through the
   discriminator
6. Test: existing 112 tests green; ratchet count unchanged

Risk: the call-site updates touch many files; one-shot PR keeps the
trame template paths and runtime behaviour stable.

## What's after P0.5

| Session | Phase(s) | Major deliverables |
|---|---|---|
| 3 | P1.a | Technique enum + manifest registry + lazy `importlib` discovery; SC manifest stub re-exporting current views |
| 4 | P1.b | Agent parametrisation: PhaseManager, prompt composer, BRIDGED_SUBMODELS, action_fns; TabKey + navigate_to_tab refactor |
| 5-8 | P2 | Single-crystal code moves (one file per commit + shims); MainViewModel one-shot rename; ratchet → 0 |
| 9 | P3 | Manifest-driven dispatcher; selector gating; CORELLI tab 5 |
| 10 | P3a | EIC decomposition; EICRowBuilder protocol |
| 11 | P4 | SANS technique skeleton |
| 12 | P5 | USANS beamline plug-in |
| 13 | P6 | Docs + acceptance check |
