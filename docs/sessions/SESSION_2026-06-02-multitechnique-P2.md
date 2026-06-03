# Session 2026-06-02: Multi-Technique Refactor — Phase 2 (models moved)

Branch: `multibeamline`.
Tests: **142** green throughout (no behaviour change — physical moves only).
Plan: [`MULTI_TECHNIQUE_PLAN.md`](../../MULTI_TECHNIQUE_PLAN.md).
Predecessor: [`SESSION_2026-06-02-multitechnique-P1b.md`](SESSION_2026-06-02-multitechnique-P1b.md).

## Objective

P2 physically relocates single-crystal code from `app/` to
`techniques/single_crystal/`, one move per commit with a re-export shim left at
the old path, driving the technique-coupling ratchet toward zero. This session
moved **all the models** (the cleanest part of P2). Views + the view-model
decomposition remain (see "What's left").

## Move mechanics (the pattern, validated on every commit)

For each moved module:
1. `git mv` into `techniques/single_crystal/...`.
2. Fix relative-import depth for the new nesting (`...core` → `....core`; the
   `temporal_analysis/` package, one level deeper, went `....core` → `.....core`).
3. Leave a re-export shim at the old `app/...` path:
   `from ...techniques.single_crystal.models.<x> import *`. Importers
   (`main_model`, views) stay unchanged — they resolve through the shim.
4. Update the ratchet baseline: drop the moved file's row. Where the shim's
   import line carries a ratchet token (`gonio_pvs`, `angle_plan`,
   `temporal_analysis`), add a row of `1` for the shim (removed at P2.18); the
   shim docstrings avoid the token (e.g. "angle-plan" hyphenated) so only the
   import line counts.

## Commits

- `a885b48` — **experiment_info** model (pattern-setter; no sibling deps).
- `ccdc0c6` — **5 leaf models**: `gonio_pvs`, `angle_plan_engine`,
  `css_status`, `data_analysis`, `newtabtemplate`. (`angle_plan_engine`'s only
  reference was already-broken dead code in `main.py` — `..model.angle_plan_engine_`,
  a path that doesn't exist.)
- `f3dd60b` — **angle_plan** model (moved after `gonio_pvs` so its
  `from . import gonio_pvs` resolves to the moved sibling).
- `4ffcddc` — **temporal_analysis** package. Core depth 4→5 dots; the lazy
  `from ..main_model import MainModel` calls became absolute
  (`exphub.app.models.main_model`) since `main_model` stays in `app`. Module
  shim at `app/models/temporal_analysis.py`; `test_peak_selectors` updated to
  the new `…selectors` path (a submodule, so the module shim can't cover it).

`exphub/techniques/single_crystal/models/` now holds: `experiment_info`,
`angle_plan`, `angle_plan_engine`, `gonio_pvs`, `css_status`, `data_analysis`,
`newtabtemplate`, and the `temporal_analysis/` package.

## Test gates met (every commit)

- ✅ 142 tests green
- ✅ Technique-coupling ratchet strictly non-increasing; moved files' rows
  dropped, residual shim tokens tracked (each ≤1)
- ✅ Beamline-coupling ratchet zero; `ruff` clean on shims + moved files;
  `mypy` clean on moved modules and `core/beamline/`
- ✅ Bind-surface contract test (`test_viewmodel_surface`) unchanged

## Also done this session

- **P2.9** `agent/validation.py` → `techniques/single_crystal/agent/validation.py`
  (commit `ae4ada1`). Pure functions, no relative imports; shim at the old path
  keeps `agent.py` + tests importing unchanged. No ratchet impact (agent/ is
  unscanned).

## The view layer is a coupled cluster (centered on MainViewModel)

Investigation finding that shapes the remaining order:

- All 5 views import `from ..view_models.main import MainViewModel` (and two
  also import `...core.beamline.active`). They touch *no* models directly.
- `view_models/angle_plan.py` imports `MainViewModel` (sibling `main`),
  plus a mix of **moved** models (`angle_plan_engine`, now in techniques) and
  **not-moved** ones (`main_model`, `plotly`, `pyvista` — these stay in
  `app/models`). Moving it requires absoluteising several app-pointing imports.

So the views + `view_models/angle_plan` + `main.py` form one unit hanging off
`MainViewModel`. Moving the views/view-model *before* P2.16 means temporary
absolute `exphub.app.view_models.main` imports that P2.16's rename must rewrite
anyway. Cleanest is to treat **P2.16 (the decomposition/rename) as the lynchpin
of this cluster** and do it together with the view/view-model moves in a
focused, carefully-tested sequence rather than piecemeal.

## Also done (later in the session)

- **P2.11–P2.15** the 5 tab views → `techniques/single_crystal/views/`
  (commit `61748d4`). Each imported only `MainViewModel` (annotation) + core;
  repointed `MainViewModel` to absolute `exphub.app.view_models.main` (P2.16
  rewrites this), fixed core depth, shims at `app/views/`. Ratchet: dropped the
  `experiment_info` view row; `angle_plan` / `temporal_analysis` view shims
  carry their token (3 → 1 each).

## What's left in P2 — see top-level `MULTI_TECHNIQUE_P2_REMAINING.md`

The remainder is one coupled cluster (everything hangs off `MainViewModel`):
P2.10 (`view_models/angle_plan.py`), **P2.16** (decompose `main.py` →
`AppShellViewModel` + `SingleCrystalSteeringViewModel`, the hard one), P2.17
(fixtures), P2.18 (delete all shims, ratchet → `{}`). A detailed, actionable
execution plan + the eic_control/ratchet-zero decision live in
**`MULTI_TECHNIQUE_P2_REMAINING.md`** at the repo root. Original move list:

- **P2.10** `app/view_models/angle_plan.py` → `techniques/single_crystal/view_models/`
- **P2.11–P2.15** the 5 views (`experiment_info`, `angle_plan`,
  `temporal_analysis`, `data_analysis`, `newtabtemplate`) →
  `techniques/single_crystal/views/`. These are imported by
  `tab_content_panel` and lazily by the manifest — shims cover both until P3
  rewires the dispatcher.
- **P2.16 (the hard one)** decompose `app/view_models/main.py`: one-shot rename
  `MainViewModel` → `SingleCrystalSteeringViewModel` + extract a slim
  `AppShellViewModel`; ViewState split. Touches every view + test +
  `mvvm_factory` + TOPAZ `css_status.py`. The bind-surface contract test and
  `_build_action_fns`'s `vm_method` resolution pin the contract for this.
- **P2.17** fixtures; **P2.18** delete all shims (ratchet rows → `{}`).

## Open question for end-of-P2 (flag before the ratchet-zero gate)

`app/models/eic_control.py` carries ~20 single-crystal tokens (angle-plan CSV
row building via `gonio_pvs` / `run_title_pv`) but the plan moves it to
`core/eic/` only in **P3a**, *after* P3. So the technique-coupling ratchet
cannot truthfully hit zero at end of P2 unless eic_control's SC coupling is
addressed earlier. Likely resolution: the "ratchet == 0" gate lands at end of
**P3a** (EIC decomposition), not P2 — or eic_control's CSV logic moves to the
single-crystal `eic_row_builder` during P2. Confirm with the user before P3.

## What's next

Continue P2 with the views (P2.11–P2.15), then the `MainViewModel`
decomposition (P2.16) as a dedicated, carefully-tested commit.
