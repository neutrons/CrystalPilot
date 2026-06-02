# Session 2026-06-02: Multi-Technique Refactor — Phase 1.a

Branch: `multibeamline`.
Tests: **121 → 131** all green.
Plan: [`MULTI_TECHNIQUE_PLAN.md`](../../MULTI_TECHNIQUE_PLAN.md).
Predecessor: [`SESSION_2026-06-02-multitechnique-P0.5.md`](SESSION_2026-06-02-multitechnique-P0.5.md).

## Objective

P1.a introduces the **technique-family layer** above beamlines — *additively*.
No app/core code moves yet; the single-crystal manifest lazy-imports the
existing `app/views/` so the new layer sits alongside the still-flat
composition. This is the structural skeleton the rest of P1/P2/P3 builds on.

The split (per the session plan): **P1.a = manifest + registry + SC manifest
stub**; **P1.b = wiring the agent consumers** (PhaseManager, prompt composer,
`BRIDGED_SUBMODELS`, action_fns, `TabKey` navigation, schema rebuild).

## What changed

### `core/beamline/technique.py` (new)

The technique-side mirror of `spec.py` / `registry.py`:

- `TabKey(str, Enum)` — `ipts`, `live`, `steering`, `status`, `analysis`.
  Replaces the legacy 1/2/3/5/6 ints at the manifest + agent layers (the
  trame dispatcher keeps using ints; translation happens there).
- `PhaseDefinition` / `ActionTool` — frozen dataclasses; the cross-technique
  contract for a PhaseManager phase and a chat-VM action verb. Consumed in
  P1.b; defined now to lock the contract.
- `TechniqueManifest` — frozen Pydantic model. Fields populated in P1.a:
  `id`, `display_name`, `default_tabs` (tabs 1-3), `tab_labels`,
  `tab_aliases`, `bridged_submodels`. Remaining agent-side fields
  (`phases`, `action_tools`, `prompts_dir`, `knowledge_dir`,
  `eic_row_builder`, `root_model_factory`) are part of the locked contract
  but wired to consumers in P1.b — they carry safe defaults for now.
- Registry: `register_technique`, `get_technique` (lazy
  `importlib.import_module("exphub.techniques.<id>")` on first access),
  `list_technique_ids`, `active_technique()` (reads `active().technique`),
  `_reset_for_tests`.

`core/` stays beamline-agnostic — no beamline ids in `technique.py` (the
beamline-coupling ratchet enforces this; docstrings were genericised).

### `techniques/` package (new)

- `techniques/__init__.py` — package doc; nothing imported eagerly
  (discovery is lazy, mirroring `beamlines/`).
- `techniques/single_crystal/__init__.py` — imports `manifest` to register.
- `techniques/single_crystal/manifest.py` — the `SINGLE_CRYSTAL` manifest:
  - `default_tabs` = {IPTS → ExperimentInfoView, LIVE → TemporalAnalysisView,
    STEERING → AnglePlanView}, each a lazy-import closure (keeps registration
    import-cheap; matches the css_status override idiom).
  - `tab_labels` / `tab_aliases` for all five slots (TabKey-keyed; mirrors
    the legacy `agent/constants.TAB_NAMES` / `TAB_MAP`).
  - `bridged_submodels = ("experimentinfo", "angleplan", "eiccontrol",
    "dataanalysis")` — now authoritative here; the agent's bridge starts
    reading it in P1.b.

`techniques/` is *not* scanned by either ratchet, so it may carry
single-crystal vocabulary freely.

### `core/beamline/__init__.py`

Re-exports the technique surface: `TechniqueManifest`, `TabKey`,
`PhaseDefinition`, `ActionTool`, `register_technique`, `get_technique`,
`active_technique`, `list_technique_ids`.

### Tests — `tests/test_technique_manifest.py` (new, 10 tests)

- lazy discovery via `get_technique`; `KeyError` for an unknown technique
- `active_technique()` follows the active beamline (TOPAZ + CORELLI → SC)
- `TabKey` value list is stable (breaking-change guard)
- SC declares exactly tabs 1-3; STATUS/ANALYSIS have no technique default
- each default-tab factory takes exactly one positional arg (TabFactory)
- labels exist for all five tabs; aliases resolve to valid `TabKey`s
- **invariant #3**: every `bridged_submodels` entry is an attribute of
  `MainModel`
- manifest is frozen (assignment raises `ValidationError`)

## Test gates met

- ✅ 121 → 131 tests green (+10)
- ✅ Technique-coupling ratchet unchanged — `technique.py` is new in `core/`
  with **zero** single-crystal hits; no app/core code moved
- ✅ Beamline-coupling ratchet stays at zero (genericised docstrings)
- ✅ `mypy` clean on the whole `core/beamline/` package (5 files)
- ✅ `ruff` clean on all new files

## Notes

- `PhaseDefinition` is intentionally redefined in `core/` (vs the existing
  `agent/workflow.PhaseDefinition`) so the manifest contract doesn't make
  `core/` import `agent/`. P1.b reconciles the two (the agent's PhaseManager
  starts consuming `core` `PhaseDefinition`s from the manifest).
- `TechniqueManifest` is `frozen=True` — manifests are module-level
  constants; immutability makes accidental mutation a hard error.

## What's next (Session 4: P1.b)

Wire the consumers to the manifest:
- 3-layer `compose_system_prompt` (core → technique → beamline → task)
- `PhaseManager(__init__)` takes `list[PhaseDefinition]`; move the 7 SC
  phases to `techniques/single_crystal/agent/phases.py`
- `agent/bridge` reads `bridged_submodels` / `FIELD_OWNER` from the manifest
- chat VM action_fns from `manifest.action_tools`
- `navigate_to_tab` accepts a `TabKey` (int shim retained)
- `Agent.rebuild_schema` plumbing for the v1 restart-gate
