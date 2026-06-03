# P2 Remaining: the MainViewModel-decomposition cluster

**Status as of 2026-06-02:** P2 has moved all single-crystal **models**
(`techniques/single_crystal/models/`), the agent **validation** helpers, and
the 5 **views** (`techniques/single_crystal/views/`). 142 tests green.
What remains is one tightly-coupled cluster + cleanup. This file is the
execution plan for a future session — read it top to bottom before starting,
and read the live `main.py` in full (≈1033 lines) before editing.

Plan of record: `MULTI_TECHNIQUE_PLAN.md` (P2.10, P2.16, P2.17, P2.18).
Predecessor session logs: `docs/sessions/SESSION_2026-06-02-multitechnique-P2.md`.

## Why these are one unit

Everything below hangs off `MainViewModel` (`app/view_models/main.py`):

- The 5 moved views import `from exphub.app.view_models.main import MainViewModel`
  (absolute, annotation-only; a temporary band-aid this cluster must rewrite).
- `app/view_models/angle_plan.py` imports `from .main import MainViewModel`,
  **and** `main.py` imports `from .angle_plan import angleplan_optimize`
  (`main.py:754`, lazy) — a mutual dependency.
- `mvvm_factory.create_viewmodels` builds `vm["main"] = MainViewModel(...)`;
  `main_view.py` reads `self.view_models["main"]`; `chat._build_action_fns`
  resolves action verbs against this VM via `vm_method` names.
- TOPAZ `beamlines/topaz/tabs/css_status.py` takes the VM as its factory arg.

So do P2.10 + P2.16 + P2.17 together, then P2.18 cleanup.

## Target shape (per MULTI_TECHNIQUE_PLAN.md)

Split `MainViewModel` into two classes:

1. **`AppShellViewModel`** — stays in `app/view_models/app_shell.py` (NEW slim
   class, *not* a renamed old one). Owns the technique-agnostic shell:
   - methods: `navigate_to_tab`, `switch_beamline`, `on_view_state_change`
     (beamline-selector half), `show_under_development_dialog`,
     `close_under_development_dialog`, `_push_view_state`.
   - `AppShellViewState`: `active_tab`, `beamline_id`, `beamline_options`,
     `beamline_switch_notice`, `beamline_switch_visible`,
     `is_under_development`, `is_uninterruptable`.
   - binds: `view_state_bind` (shell), and it holds the beamline selector.

2. **`SingleCrystalSteeringViewModel`** — renamed `MainViewModel`, moved to
   `techniques/single_crystal/view_models/steering.py`. Owns everything else
   in today's `main.py` (~45 methods: angle plan, coverage, HKL, temporal/CSS
   figures, EIC submit/auth, live update, run table, optimizer).
   - `SingleCrystalSteeringViewState`: `is_live_update_running`,
     `hkl_individual_menu`, `hkl_peak_ratio_menu`.
   - binds: `model_bind`, `experimentinfo_bind`, `angleplan_bind`,
     `eiccontrol_bind`, `temporalanalysis_bind`, `dataanalysis_bind`,
     `cssstatus_bind`, `newtabtemplate_bind`, and the figure-update binds
     (`temporalanalysis_updatefigure_*`, `newtabtemplate_updatefig_bind`,
     `angleplan_updatefigure_coverage_bind`).

The `_tab_to_int` / `_TAB_KEY_TO_INT` shim (already in `main.py`) moves with
`navigate_to_tab` into `AppShellViewModel`.

## How the two VMs relate (the hard design decision)

Today every view binds to ONE `MainViewModel`. After the split, views (tabs
1–3 single-crystal) need the **steering** VM; the shell (tabs panel, selector,
chat) needs the **shell** VM. Decide and document:

- `mvvm_factory.create_viewmodels` returns both, e.g. `vm["app_shell"]` and
  `vm["steering"]` (keep `vm["main"]` as an alias to steering during transition
  if it lowers churn — but the plan prefers a clean break).
- `main_view.py`: tabs/selector use the shell VM; `TabContentPanel` /
  `css_status` factories receive the **steering** VM (that's what the views
  expect). `chat` action verbs (`submit_angle_plan`, etc.) resolve against the
  **steering** VM (`vm_method`s live there) — update the `ChatViewModel`
  `main_vm=` wiring accordingly.
- `bind_surface` contract test (`tests/test_viewmodel_surface.py`) currently
  asserts all binds on `vm["main"]`. After the split, point it at the steering
  VM and add `active_tab`/selector assertions for the shell VM. Keep the
  EXPECTED_BINDS set accurate.

## Step-by-step (each step its own commit, all 142+ tests green)

1. **P2.10 — move `view_models/angle_plan.py`** →
   `techniques/single_crystal/view_models/angle_plan.py`.
   - Create `techniques/single_crystal/view_models/__init__.py`.
   - Fix imports: `from .main import MainViewModel` →
     `from exphub.app.view_models.main import MainViewModel` (still app
     pre-decomposition); `from ..models.main_model import MainModel` →
     `from exphub.app.models.main_model import MainModel` (main_model STAYS in
     app); `from ..models.plotly`/`pyvista` → absolute `exphub.app.models.*`
     (these STAY in app — they are app-shell, not single-crystal); the lazy
     `from ..models.angle_plan_engine import ...` → `from ..models.angle_plan_engine`
     now resolves inside techniques (angle_plan_engine already moved).
   - Shim at `app/view_models/angle_plan.py`:
     `from ...techniques.single_crystal.view_models.angle_plan import *`.
   - `main.py:754 from .angle_plan import angleplan_optimize` resolves via the
     shim. Ratchet row 12 → (shim token count; "angle_plan" → 1).

2. **P2.16 — the decomposition** (one commit, no delegator shim):
   - Create `app/view_models/app_shell.py` with `AppShellViewModel` +
     `AppShellViewState` (slim; see map above).
   - Move the rest of `main.py` to
     `techniques/single_crystal/view_models/steering.py`, renaming
     `MainViewModel` → `SingleCrystalSteeringViewModel` and `ViewState` →
     `SingleCrystalSteeringViewState` (keep only SC fields). Fix import depth
     (`...core`→`....core`, etc.) and the `from exphub.app.view_models.main`
     references in the 5 moved views + `view_models/angle_plan` →
     `from ..steering import SingleCrystalSteeringViewModel` (or the chosen path).
   - Rewrite `mvvm_factory.create_viewmodels` to build both VMs and wire
     `ChatViewModel(main_vm=<steering>)`, `nav_fn=<shell>.navigate_to_tab`.
   - Update `main_view.py` to use shell VM for chrome + steering VM for tabs.
   - Update `beamlines/topaz/tabs/css_status.py` if it type-hints `MainViewModel`.
   - Delete `app/view_models/main.py` (NO shim — atomic rename). Update every
     remaining importer of `MainViewModel` (grep `MainViewModel` across src +
     tests). Update `tests/test_viewmodel_surface.py`.
   - Ratchet: `app/view_models/main.py` row removed (file gone); steering VM is
     in techniques (unscanned). `app/view_models/angle_plan.py` shim row stays
     until P2.18.

3. **P2.17 — move the optimizer fixture**:
   `app/fixtures/optimizer_fallback_angles.json` →
   `techniques/single_crystal/fixtures/`. The loader
   `_load_optimizer_fallback_angles` (currently in `main.py`) moves into the
   steering VM in P2.16 — point its `Path(__file__)...` at the new fixtures dir
   then. (So really fold this into P2.16, or do immediately after.)

4. **P2.18 — delete all shims** (cleanup, one commit):
   - Delete every `app/models/*.py` and `app/views/*.py` re-export shim created
     in P2, plus `app/view_models/angle_plan.py` and `agent/validation.py`
     shims. Repoint their importers to the real `techniques/...` paths:
     - `app/models/main_model.py` imports of the moved models →
       `from ...techniques.single_crystal.models.X import Y`.
     - `app/views/tab_content_panel.py` view imports (until P3 makes it
       manifest-driven) → techniques paths.
     - `agent/agent.py` `from .validation import` → techniques path.
     - The manifest's lazy view factories (`techniques/single_crystal/manifest.py`)
       already point at `...app.views.*` — repoint to `..views.*` (the moved
       views in the same package).
   - Set `BASELINE = {}` in `tests/test_technique_coupling.py` (keep
     `core/beamline/spec.py: 2` and `app/models/eic_control.py: 20` IF the
     eic_control decision (below) defers them to P3a). Tighten `INITIAL_CAP`.

## OPEN QUESTION — resolve before the ratchet-zero gate

`app/models/eic_control.py` carries ~20 single-crystal tokens (angle-plan CSV
row building via `gonio_pvs` / `run_title_pv`). The plan moves it to
`core/eic/` only in **P3a** (after P3). So either:

- (a) the "ratchet == 0" gate lands at end of **P3a**, not P2 (leave
  `eic_control.py: 20` + `core/beamline/spec.py: 2` in BASELINE through P3); or
- (b) pull eic_control's CSV-row logic into the single-crystal
  `eic_row_builder` (the P3a seam) early, during P2.18.

Recommend (a): it matches the plan's layering and keeps P2 scoped to file
moves. Flag to the user.

## Invariants to keep green at every step

- 142+ tests pass; `test_viewmodel_surface` updated but still pins the bind
  surface; `test_app` (`MainApp()` constructs) passes.
- Technique-coupling ratchet strictly non-increasing; beamline-coupling zero.
- `ruff` + `mypy` clean on touched/new files (`core/beamline/` must stay
  mypy-clean; pre-existing main.py mypy errors are acceptable to carry into the
  steering VM but don't ADD new ones).
- Run via the pixi env: `.pixi/envs/default/bin/python -m pytest -q`.

## Shim/token recipe (proven in P2 model/view moves)

- Move: `git mv`; fix relative-import depth for the new nesting; leave
  `from <newpath> import *  # noqa: F401, F403` at the old path.
- If the shim's import path contains a ratchet token (`angle_plan`,
  `temporal_analysis`, `gonio_pvs`), keep the docstring token-free (hyphenate,
  e.g. "angle-plan") so only the import line counts; add/keep a BASELINE row
  of `1`. Remove the row when the shim is deleted at P2.18.
