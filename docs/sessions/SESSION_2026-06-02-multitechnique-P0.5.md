# Session 2026-06-02: Multi-Technique Refactor — Phase 0.5

Branch: `multibeamline`.
Tests: **112 → 121** all green.
Plan: [`MULTI_TECHNIQUE_PLAN.md`](../../MULTI_TECHNIQUE_PLAN.md).
Predecessor: [`SESSION_2026-06-02-multitechnique-P0.md`](SESSION_2026-06-02-multitechnique-P0.md).

## Objective

P0.5 migrates `BeamlineSpec` from a flat bag of single-crystal-shaped
fields to a **discriminated union** keyed on `kind`, *before* any files
move in P2. Doing the spec-shape change and the call-site updates together
in one pre-move PR keeps them out of P2's file-move churn.

The driving problem (from the P0 audit): a fixed single-crystal shape with
22 `Optional[X]` fields would be a tech-debt time-bomb. A discriminated
union gives each technique family a clean config from day one and lets
mypy narrow the union at every read site.

## What changed

### Spec shape (`core/beamline/spec.py`)

New discriminated payload, selected by `kind`:

- `SingleCrystalConfig(kind="single_crystal")` — `goniometer`, `mantid`,
  `default_calibration`, `default_spectra`, `run_title_pv`,
  `bob_screen_path`, `bob_macros_path`, `extra_subscribe_pvs`.
- `SansConfig(kind="sans")` — minimal stub for shape parity:
  `mantid_instrument_name`, `default_q_range`, `transmission_monitor_pv`,
  `live_stream_url` (all `Optional`, all `None`). No USANS spec yet (P5).
- `TechniqueConfig = SingleCrystalConfig | SansConfig` type alias.

`BeamlineSpec` gains:

- `technique: Literal["single_crystal", "sans"] = "single_crystal"` —
  a cheap discriminator for manifest lookup / selector gating that doesn't
  require touching the union.
- `technique_config: SingleCrystalConfig | SansConfig =
  Field(default_factory=SingleCrystalConfig, discriminator="kind")`.
- `@model_validator(mode="after") _sync_technique` — derives `technique`
  from `technique_config.kind` (the authoritative discriminator), so a
  mismatched `technique=` kwarg is corrected rather than silently wrong.
- `single_crystal` property — narrows the union to `SingleCrystalConfig`,
  raising a clear `TypeError` for a non-SC payload instead of letting an
  `AttributeError` surface deep in a call site.

Fields **removed** from the flat spec (moved into `SingleCrystalConfig`):

- `BeamlineSpec.goniometer`, `BeamlineSpec.mantid`
- `PathsSpec.default_calibration`, `PathsSpec.default_spectra`
- `EICSpec.run_title_pv`
- `DetectorSpec.bob_screen_path`, `DetectorSpec.macros_path`
  (→ `bob_macros_path`), `DetectorSpec.extra_subscribe_pvs`

`DetectorSpec` keeps the genuinely cross-technique fields:
`detector_layout`, `pixel_dims`, `monitor_pvs`.

### Call sites updated to read through the discriminator

- `core/beamline/context.py` — `angle_pv`, `ramp_pv`, `charge_pv`,
  `angle_columns`, `angle_axis_keys`, `bob_screen`, `bob_macros`,
  `extra_subscribe_pvs` now read `spec.single_crystal.*`.
- `core/paths/resolver.py` — `default_calibration` reads
  `spec.single_crystal.default_calibration`.
- `app/models/experiment_info.py` — instrument name + default
  calibration/spectra (4 sites).
- `app/models/eic_control.py` — instrument→code map (2 sites) +
  `run_title_pv`.
- `app/models/angle_plan.py` — instrument name + `run_title_pv`.
- `app/models/temporal_analysis/workflow.py` — instrument name.

`app/views/temporal_analysis.py` reads `detector.monitor_pvs`, which stays
on `DetectorSpec` — **no change**.

### Beamline specs migrated

TOPAZ and CORELLI now set `technique="single_crystal"` and carry their
goniometer / Mantid / calibration / run-title / `.bob` values under
`technique_config=SingleCrystalConfig(...)`. Their `detector`, `paths`,
`eic` blocks shrank to the cross-technique fields.

### Tests

New `tests/test_technique_config.py` (9 tests):

- TOPAZ + CORELLI carry a `SingleCrystalConfig` with the right values
- context reads goniometer + screen through the discriminator
- bare spec defaults to single-crystal
- `technique` synced from `technique_config.kind`; mismatched kwarg corrected
- discriminator parses a dict payload to the right subclass
- `single_crystal` accessor raises `TypeError` on a SANS payload
- `SansConfig` stub fields default to `None`

## Test gates met

- ✅ All previously-green tests still pass (112 → 121, +9 new)
- ✅ Technique-coupling ratchet unchanged: `spec.py` still 2
  (`angle_plan` + `temporal_analysis` field names in `TabOverrides`);
  `context.py` and `resolver.py` still 0; app/* counts unchanged
- ✅ Beamline-coupling ratchet stays at zero
- ✅ `mypy` clean on `core/beamline/spec.py` (also context.py, resolver.py,
  corelli/spec.py). Pre-existing `no-untyped-def` on TOPAZ's
  `_build_css_status` lazy factory is unrelated to P0.5 and left as-is.

## Notes

- `ruff` errors observed on the touched files (EICSpec D101, resolver
  `Path` F401 + `ensure_dir` docstring, angle_plan E501, eic_control B023)
  are all **pre-existing on HEAD** — left untouched to keep the P0.5 diff
  focused. Only the new test file's import sort was fixed.
- `technique_config` has a `default_factory` so a bare `BeamlineSpec`
  (e.g. in a future test) still constructs as single-crystal.

## What's next (Session 3: P1.a)

Technique enum + manifest + registry; lazy `importlib` discovery;
`techniques/single_crystal/manifest.py` stub re-exporting current views.
The discriminated config is now in place for the manifest to build on.
