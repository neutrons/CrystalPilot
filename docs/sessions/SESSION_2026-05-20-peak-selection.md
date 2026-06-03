# Session 2026-05-20: Live-Data Tab — Peak-Selection Modes

Branch: `multibeamline` (continuing from the multi-beamline refactor).
Total commits this session: **4**.
Tests: **83 → 102** all green at every commit.
Net source delta: +1313 / −1490 (refactor net-shrink + feature work).

## Objective

Make the Live Data Processing tab's "Peak Selection" dropdown actually
drive what gets plotted. Pre-session, the dropdown carried 5 options but
only `All Peaks` and `Max Peak` had implementations; the other three
silently fell through and left whatever `intensity_ratio` was last set.

User-requested behavior:

| Mode | Peak subset | Top-figure scalar | Bottom-figure scalar |
|---|---|---|---|
| All Peaks | all indexed peaks | `Mean ((I)/sd(I))` (from `StatisticsOfPeaksWorkspace`) | `100 / (I/σ)` |
| Bragg Peaks | indexed peaks with `IntMNP == (0,0,0)` | mean `I/σ` over subset | `100 / mean(I/σ)` |
| Satellite Peaks | indexed peaks with `IntMNP != (0,0,0)` | mean `I/σ` over subset | `100 / mean(I/σ)` |
| Max Peak | brightest single peak | `I/σ` of that peak | `100 / (I/σ)` |
| Diffuse Scattering | placeholder | `None` (waits) | `None` |
| Individual Peak `[h,k,l]` | one peak matched by HKL | `I/σ` of that peak | `100 / (I/σ)` |
| Peak Ratio `[h₁,k₁,l₁]/[h₂,k₂,l₂]` | two peaks | `I_a / I_b` (raw intensity ratio) | `σ(ratio)/ratio × 100 (%)` |

The two new modes need user-supplied HKL input. UX chosen: a small
`VChip` next to the dropdown shows the currently-bound HKL; clicking
opens an anchored `VMenu` popover with the integer inputs + an Apply
button (no centered modal — figures stay visible).

Additional request, mid-session: save a copy of the current figure
**plus its data** to the same folder as the UB `.mat` after every
reduction cycle.

## Background

The pre-session live-data code was a 1421-line monolith
`models/temporal_analysis.py` containing `MantidWorkflow` (Mantid
orchestration + per-cycle state) glued to `TemporalAnalysisModel`
(pydantic + figure builders) in one module. The peak-selection logic
was a 9-line if/elif chain in the middle of a 280-line god-method
(`live_data_reduction.check_peaks_of_current_run`). One inline branch
(`"Total Peaks"`) was dead — its label wasn't even in the dropdown.
Figure builders were 130 lines each with nested `if prediction_model_type`.

Adding new modes on top of that surface would have produced an `N×M`
grid of inline if-branches across two god-methods. The session
therefore opened with a refactor before any feature work.

## Approach

Three-phase rollout, each commit independently revertable:

1. **Refactor only** — split the file into a package, lift the 5
   inner pipeline closures, introduce a `PeakSelector` Protocol with
   `make_selector(name, **params)` as a registry-driven dispatch.
   Behaviour preserved exactly (including the SaveIsawUB-with-`.integrate`-
   filename quirk and the uncertainty-figure-guards-on-measure_times
   quirk).
2. **Backend feature** — five new selector classes; `SelectionResult`
   gains optional title/axis overrides for peak-ratio's "I_a / I_b"
   (which doesn't fit "Signal Noise Ratio"); pipeline honors `None`
   from selectors (skip cycle, no buffer append); per-cycle figure
   snapshot saved alongside UB `.mat`.
3. **UI** — chip + popover for the two HKL-requiring modes; mode change
   auto-stops the live loop and clears plot buffers (different modes
   plot different units; mixing them is misleading).

A fourth commit landed a fix for two browser-side bugs that headless
testing couldn't catch.

---

## Implementation — Phases 1–4

### Phase 1 — Refactor (1 commit)

#### `bdc7ac8` — split 1421-line file into package; add selector seam

Convert `models/temporal_analysis.py` into a 7-file package:

```
src/exphub/app/models/temporal_analysis/
├── __init__.py      re-exports for back-compat
├── _debug.py        DEBUG_LIVE env-var + trace() helper
├── selectors.py     PeakSelector protocol, AllPeaks, MaxPeak, registry
├── pipeline.py      five top-level functions (was inner closures):
│                      run_change_checkpoint, load_config, refine_ub,
│                      integrate_and_predict, check_peaks
├── figures.py       pure build_intensity_figure / build_uncertainty_figure
├── workflow.py      MantidWorkflow: state buckets + StartLiveData lifecycle
└── model.py         TemporalAnalysisModel pydantic + figure dispatch + cache
```

The selection switch in `check_peaks` is replaced with a one-line
dispatch: `selector = make_selector(wf.selection, **wf.selector_params)`,
`wf.intensity_ratio = result.intensity_ratio`. Unknown names return
`None` and preserve legacy fall-through.

- Old import path `from ..models.temporal_analysis import TemporalAnalysisModel`
  resolves unchanged via the package `__init__.py`.
- 165-line commented-out dead `PoissonModelAnalysis` block dropped.
- Test count unchanged (83); MainApp constructs end-to-end.

### Phase 2 — New selector modes + snapshot save (1 commit)

#### `1c16ef8` — 5 new peak-selection modes + per-cycle figure snapshot

**selectors.py** — five new classes registered in `SELECTOR_REGISTRY`:

- `BraggPeaksSelector` — filter `_mnp_is_zero(peak)`, reduce by mean I/σ.
- `SatellitePeaksSelector` — filter `not _mnp_is_zero(peak)`, same reduction.
- `MaxPeakSelector` — existing, hardened against invalid max_idx / zero σ.
- `DiffuseScatteringSelector` — always returns `None` (placeholder).
- `IndividualPeakSelector(hkl)` — `_find_peak_by_inthkl` linear scan,
  returns I/σ of the matched peak.
- `PeakRatioSelector(hkl_a, hkl_b)` — two HKL lookups, returns
  `SelectionResult(intensity_ratio=I_a/I_b, rsig=√((σ_a/I_a)²+(σ_b/I_b)²)·100,
  intensity_yaxis="I_a / I_b", uncertainty_yaxis="σ(ratio)/ratio (%)")`.

`SelectionResult` gains four optional label-override fields
(`intensity_title`, `intensity_yaxis`, `uncertainty_title`,
`uncertainty_yaxis`); modes that don't set them get figure defaults.
The registry's factory lambdas accept and ignore unused kwargs so the
workflow can fire `hkl=`, `hkl_a=`, `hkl_b=` at every selector each cycle.

`_mnp_is_zero` tolerates Mantid versions that pre-date `getIntMNP` —
treats every peak as Bragg when the attribute is unavailable.

**pipeline.py:check_peaks** — `result is None` now means "skip this
cycle"; sets `wf.skip_this_cycle = True`, no buffer append, no Rsig
recompute. Successful selectors park their labels on `wf.current_labels`
for the figure builder to pick up.

**workflow.py** — new attrs: `selector_params`, `selection_aux`,
`current_labels`, `skip_this_cycle`. `update_experiment_info` reads the
three HKL fields off `models.temporalanalysis` into `selector_params`.
`intensity_ratio` / `Rsig` seeded to `0.0` so legacy fall-through
doesn't trip a first-cycle AttributeError.

**figures.py** — builders gain optional `title=` / `yaxis=` overrides
(Peak Ratio mode plots `I_a/I_b`, which doesn't fit "Signal Noise
Ratio"). New `waiting_figure(title, yaxis)` public helper. New
**`save_figure_snapshot(output_dir, file_prefix, intensity_fig=,
uncertainty_fig=, measure_times=, intensity_ratios=, rsigs=,
proton_charges=)`** writes three files:

- `<prefix>_intensity.html`    interactive top plot
- `<prefix>_uncertainty.html`  interactive bottom plot
- `<prefix>_data.csv`          columns `time_s, proton_charge_C,
                               intensity_ratio, rsig_or_uncertainty_pct`

Silent-fail on per-file errors (the snapshot runs every cycle and must
not raise).

**model.py** — dropdown now has all 7 modes (renamed `"Diffuse scattering"`
→ `"Diffuse Scattering"` for consistent capitalisation). Three new
pydantic fields `individual_peak_hkl: List[int]`, `peak_ratio_hkl_a/b`
hold user input. `on_data_selection_change(new, old)` clears the
workflow's plot buffers and invalidates figure caches. `Diffuse
Scattering` mode short-circuits the figure builders and returns
`waiting_figure(...)` regardless of workflow state. New
`save_latest_figure_snapshot()` method composes the prefix
`live_<bl>-ipts-<N>_run-<run>_<timestamp>` and calls the figures-module
helper.

**view_models/main.py** — `temporalanalysis_bind` now has a user-change
callback `on_temporalanalysis_change` that detects dropdown changes,
clears buffers, auto-stops the live loop, and snackbar-prompts the user
to restart. `_handle_plot_definition_change(reason)` factored out for
reuse between dropdown changes and HKL applies. `get_live_mtd_data` now
calls `save_latest_figure_snapshot` via thread executor after each cycle.

**tests/test_peak_selectors.py** — 19 stub-`Peak`-driven tests
exercising every selector class, label overrides, registry
membership, kwarg-ignore on the factory. **83 → 102 tests.**

### Phase 3 — Chip + popover HKL editor UI (1 commit)

#### `bf6e02c` — chip+popover HKL editor for Individual / Peak Ratio modes

`ViewState` gains `hkl_individual_menu: bool` and `hkl_peak_ratio_menu:
bool` for the `v-model` bindings of the two VMenus.

`MainViewModel` gains:

- `apply_individual_hkl()` — clears buffers, pauses live loop, sets
  `hkl_individual_menu = False` (closes the popover).
- `apply_peak_ratio_hkls()` — same, with both HKLs in the snackbar.

The buffer-clear path was promoted to a public `clear_plot_buffers()`
helper on the model so both dropdown changes and HKL applies route
through it (`on_data_selection_change` became a thin no-op-on-same-mode
wrapper).

`views/temporal_analysis.py` — the controls row's middle column wraps
the dropdown + two chips in a `display:flex` row. Each chip carries
`v-if` on its data_selection match; clicking the chip opens its
companion `VMenu` (anchored via `activator="#chip-id"`,
`v_model=("controls.hkl_*_menu", False)`, `close_on_content_click=False`).
Inside: 3 or 6 integer InputFields + an Apply VBtn whose click handler
is `self.view_model.apply_*_hkl`.

### Phase 4 — Browser-bug fix (1 commit)

#### `0f68c83` — scalar HKL fields + v-show chips so popover inputs commit

Two issues surfaced when the UI was tested in-browser:

1. **`v-model="array[0]"` didn't round-trip.** Trame's state diff
   tracks field-level writes; in-place array-index mutation on the
   client side isn't replicated to the pydantic model on the server.
   The InputFields displayed values fine but typing didn't commit.
2. **`VMenu` `activator="#chip-id"` selector ran at component mount.**
   With `v-if` on the chip, the element didn't exist at first render
   (when the dropdown defaulted to "All Peaks"), so `querySelector`
   returned `null` and the menu permanently failed to anchor — even
   after the chip later appeared.

Fix:

- `model.py`: replace the three `List[int]` fields with **nine scalar
  `int` fields** (`individual_peak_h/k/l`, `peak_ratio_a_h/k/l`,
  `peak_ratio_b_h/k/l`). Add three `@property` tuple accessors
  (`individual_peak_hkl`, `peak_ratio_hkl_a`, `peak_ratio_hkl_b`) so
  the workflow side doesn't have to know the storage layout.
- `workflow.update_experiment_info`: assemble the tuples from the
  scalars into `wf.selector_params`.
- `views/temporal_analysis.py`: **`v-if` → `v-show`** on both chips
  (DOM always present, activator selector resolves); add explicit
  `click="controls.hkl_*_menu = !controls.hkl_*_menu"` as a
  belt-and-suspenders toggle; all `v-model` bindings switched from
  `array[idx]` to scalar field names; chip-text templates updated to
  display scalars directly.
- `view_models/main.py`: snackbar messages read scalars directly.

Selector tests are tuple-based and didn't notice the storage change.
Tests stayed at 102.

---

## Outcome

### Quantitative

| Metric | Before session | After session |
|---|---|---|
| `temporal_analysis.py` lines | 1421 (one file) | 7 files, ~1430 LOC + 1 stub-test file |
| Implemented dropdown modes | 2 (`All Peaks`, `Max Peak`) | **7** (all dropdown options live) |
| Tests | 75 (pre-multibeamline) → 83 | **102** |
| New selector tests | 0 | 19 |
| Figure label overrides per mode | hardcoded in figures.py | Per-`SelectionResult` |
| Per-cycle persistence | UB `.mat` only | UB `.mat` + figure HTML × 2 + data CSV |
| Mode-change handling | Mixed-unit history left on screen | Buffers cleared + loop auto-paused + snackbar |
| Hardcoded TOPAZ/BL12 outside `beamlines/` | 0 | **0** (no regression) |

### Files touched

**New files (under `src/`):**
- `app/models/temporal_analysis/__init__.py`
- `app/models/temporal_analysis/_debug.py`
- `app/models/temporal_analysis/selectors.py`
- `app/models/temporal_analysis/pipeline.py`
- `app/models/temporal_analysis/figures.py`
- `app/models/temporal_analysis/workflow.py`
- `app/models/temporal_analysis/model.py`

**Deleted:**
- `app/models/temporal_analysis.py` (single-file module)

**Modified (under `src/`):**
- `app/view_models/main.py` — ViewState fields, callbacks, snapshot wiring
- `app/views/temporal_analysis.py` — chip + popover row

**New tests:**
- `tests/test_peak_selectors.py`

### Commits

```
0f68c83 temporal_analysis: scalar HKL fields + v-show chips so popover inputs commit
bf6e02c temporal_analysis: chip+popover HKL editor for Individual / Peak Ratio modes
1c16ef8 temporal_analysis: 5 new peak-selection modes + per-cycle figure snapshot
bdc7ac8 temporal_analysis: split 1421-line file into package; add selector seam
```

### Design points worth remembering

- **Selector registry is the single seam.** Adding a new mode = write a
  class with `name` + `select(...)` + register it in
  `SELECTOR_REGISTRY`. Nothing else touches `check_peaks` or the
  figures.
- **`SelectionResult.aux` is the future seam for richer plots.** Today
  every mode boils down to one scalar appended to `intensity_ratios`.
  When a mode needs to plot a different shape (e.g. per-peak history
  side-by-side), the selector parks the data in `result.aux` and a new
  builder in `figures.py` reads from `wf.selection_aux` instead of
  `wf.intensity_ratios`.
- **Trame v-model gotcha.** Don't bind to array indices
  (`v-model="list[0]"`) — it shows values but doesn't write back.
  Use scalar pydantic fields; expose tuples via `@property` if the
  business logic needs them.
- **VMenu activator gotcha.** A v-if'd activator that doesn't exist at
  mount time is permanently broken. Either use v-show (DOM present,
  display:none when hidden) or use an explicit click handler that
  toggles the menu's `v-model` directly.

---

## What's left

1. **Satellite mode currently always reports an empty subset.** The
   selector filters correctly on `IntMNP != (0,0,0)`, but the pipeline's
   `IndexPeaks` calls don't pass `ModVector1/2/3` or `MaxOrder`, so every
   peak ends up with `IntMNP == (0,0,0)`. `MantidWorkflow.__init__`
   already declares `mod_vector1/2/3`, `max_order`, `cross_terms`
   (hardcoded defaults). To wire end-to-end you need to (a) source
   these from `experimentinfo` (which may need new pydantic fields),
   and (b) pass them into the `IndexPeaks` calls in
   [pipeline.py](../../src/exphub/app/models/temporal_analysis/pipeline.py).
   Selector code is already correct; this is upstream-only work.
   **Probably its own session — touches the ExperimentInfo model too.**

2. **Diffuse Scattering is a placeholder.** `DiffuseScatteringSelector.select()`
   returns `None`; figures show "Waiting for data". When the actual
   diffuse-scattering reduction is specified, replace the selector body.
   Everything around it (figure dispatch, mode-change buffer clear,
   snapshot save) already handles the placeholder gracefully.

3. **Browser-side polish for the chip+popover** (verify in session
   2026-05-21 or later):
   - Popover positioning may need tuning — `VMenu(location="bottom")`
     can be swapped for `"end"` (right-of-chip) or `"bottom start"`
     (bottom-left).
   - If `VMenu` activator + `v-show` still misbehaves in some
     edge case, fallback is to swap `VMenu` for `VDialog` (centered
     modal) — one-line change per popover.
   - Number inputs are tiny (`density="compact"`); spinners may not
     render usable arrows. If users find them awkward, drop
     `density="compact"` or grow `min-width`.

4. **Modulation-vector UI** (depends on #1). Once modulation params are
   pulled from experimentinfo, the user needs a way to set them. The
   experiment-info tab is the natural home.

## Suggested next session

- **#1 above** is the highest-value next step — it makes the Satellite
  selector functional without any new UI for it. Estimate: pipeline.py
  edits (15 lines) + experimentinfo new fields (3 lines × 3 ModVector
  + 1 MaxOrder) + view edit to surface them + a test that satellite
  peaks appear when modulation is configured. Probably one commit.
- **#2** is open-ended (depends on a physicist defining the diffuse
  reduction).
- **#3** is iterative browser tuning, fold into whichever session next
  touches the live-data tab.
