# Session 2026-06-02: Multi-Technique Refactor — Phase 1.b (partial)

Branch: `multibeamline`.
Tests: **131 → 136** all green.
Plan: [`MULTI_TECHNIQUE_PLAN.md`](../../MULTI_TECHNIQUE_PLAN.md).
Predecessor: [`SESSION_2026-06-02-multitechnique-P1a.md`](SESSION_2026-06-02-multitechnique-P1a.md).

## Objective

P1.b wires the agent's hardcoded single-crystal behaviour to the technique
manifest introduced in P1.a, so a future SANS/USANS technique needs no
agent-side patches. This session lands the three highest-value, well-bounded
items; the agent-tool-surface items are deferred (see "What's left").

## What changed (3 commits)

### `5f3b2ad` — 3-layer prompt composer

`compose_system_prompt` now inserts a **technique-context** layer between the
beamline-agnostic core identity and the per-beamline context:

    core_identity → technique context → beamline context → task

- `techniques/single_crystal/prompts/context.md` — technique-level fragment
  (UB matrix, HKL indexing, angle plan, peak finding) shared by every
  single-crystal beamline. `manifest.prompts_dir` points at it.
- Fixed a latent P1.a bug: `_reset_for_tests()` now also evicts cached
  `exphub.techniques.*` modules, so lazy re-discovery re-registers. It
  surfaced only once the composer imported the technique module before the
  reset test ran.

### `5652dba` — bridge sources from the manifest

- `bridge.BRIDGED_SUBMODELS` / `FIELD_OWNER` constants replaced by
  `bridge.bridged_submodels()` / `bridge.field_owner()`, which read the
  active technique manifest.
- `TechniqueManifest` gains `field_owner`; the single-crystal manifest
  populates it (+`bridged_submodels`).
- Consumers updated: `mvvm_factory`, `view_models/chat`. `test_agent`
  monkeypatch sites updated (constant → function).

### `effe598` — PhaseManager + navigate_to_tab via manifest / TabKey

- `PhaseManager` is now instance-based and takes a phase list, defaulting to
  `active_technique().phases`. The 7 single-crystal phases moved out of
  `agent/workflow.py` to `techniques/single_crystal/agent/phases.py`.
- core `PhaseDefinition` gains `label` (per-phase display name; `tab` is a
  `TabKey`). PhaseManager/handlers use `.label` (was `tab_name`).
- `MainViewModel.navigate_to_tab` accepts `TabKey | int`; a `_tab_to_int`
  shim maps TabKey → the dispatcher's legacy int (ints pass through).
  handlers pass `phase.tab` (TabKey) to `nav_fn`.
- `manifest.phases` populated for single_crystal.

## Test gates met

- ✅ 131 → 136 tests green (+5: prompt layer, manifest phases, PhaseManager
  default/explicit, navigate TabKey shim)
- ✅ Technique-coupling ratchet unchanged — `technique.py` in `core/` stays
  at zero SC hits; the moved phases live in `techniques/` (unscanned); no
  app/core code moved
- ✅ Beamline-coupling ratchet stays at zero
- ✅ `mypy` clean on `core/beamline/`; no new mypy/ruff errors in the touched
  agent/app files (verified pre-existing ones against HEAD)

## What's left in P1.b (not started)

1. **Agent action verbs from the manifest** — `tools.py` still hardcodes the
   5 single-crystal action tools (submit_angle_plan, authenticate_eic,
   initialize_strategy, upload_strategy, stop_run) and `chat._build_action_fns`
   maps them to MainViewModel methods. To make them manifest-driven the
   `ActionTool` contract needs a VM-method reference and `tools.py` must
   generate the action tools dynamically. This rewrites the LLM-facing tool
   surface — deferred as its own commit.
2. **`Agent.rebuild_schema(main_model)`** — additive plumbing for the v1
   "restart required for cross-technique" gate (called from `switch_beamline`).
3. **`tests/test_viewmodel_surface.py`** — contract test pinning the SC VM's
   `*_bind` surface (lands with the bind names locked).

## What's next

Finish P1.b (items above), then P2 (move single-crystal code under
`techniques/single_crystal/`, one file per commit + shims; ratchet → 0).
