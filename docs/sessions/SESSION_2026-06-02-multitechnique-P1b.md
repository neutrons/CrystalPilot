# Session 2026-06-02: Multi-Technique Refactor — Phase 1.b

Branch: `multibeamline`.
Tests: **131 → 142** all green.
Plan: [`MULTI_TECHNIQUE_PLAN.md`](../../MULTI_TECHNIQUE_PLAN.md).
Predecessor: [`SESSION_2026-06-02-multitechnique-P1a.md`](SESSION_2026-06-02-multitechnique-P1a.md).

## Objective

P1.b wires the agent's hardcoded single-crystal behaviour to the technique
manifest introduced in P1.a, so a future SANS/USANS technique needs no
agent-side patches. **All P1.b items landed** (originally split across two
sittings; the second completed the action-tool surface + plumbing).

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

### `e4d47ad` — agent action verbs from `manifest.action_tools`

- `ActionTool` gains `vm_method` + `success_message` (drops the unused
  `handler`); the single-crystal manifest declares its 5 verbs.
- `tools.py` no longer hardcodes those 5 `@tool` functions — `_make_action_tool`
  generates one LangChain tool per spec, calling the resolved callable.
  `make_tools` / `Agent` gain an `action_tools` param.
- `chat._build_action_fns(action_tools)` resolves each `spec.vm_method` against
  the live view-model.

### `0c5d3d1` — `Agent.rebuild_schema` + bind-surface contract test

- `Agent` stores its tool-construction inputs and gains `rebuild_schema()`
  (rebuilds tools + graph against a new schema). The `switch_beamline` call
  site lands with P3's selector gating; this is the plumbing it will use.
- `tests/test_viewmodel_surface.py` pins the steering VM's `*_bind` surface,
  built on an isolated named trame server (so it doesn't collide with
  `test_app`'s `MainApp()` on the default singleton server). Locks the
  contract for P2's VM move.

## Test gates met

- ✅ 131 → 142 tests green (prompt layer, manifest phases, PhaseManager
  default/explicit, navigate TabKey shim, action-tool generation, rebuild
  plumbing, bind-surface contract)
- ✅ Technique-coupling ratchet unchanged — `technique.py` in `core/` stays
  at zero SC hits; the moved phases live in `techniques/` (unscanned); no
  app/core code moved
- ✅ Beamline-coupling ratchet stays at zero
- ✅ `mypy` clean on `core/beamline/`; no new mypy/ruff errors in the touched
  agent/app files (verified pre-existing ones against HEAD)

## Deferred to P3 (by design)

- The `switch_beamline` → `Agent.rebuild_schema` call site lands with P3's
  selector gating + `on_deactivate()` lifecycle work. P1.b only adds the
  method (the plumbing); v1 still requires an app restart to switch technique.

## What's next

P1 is complete (P1.a manifest/registry + P1.b agent parametrisation). The
agent no longer hardcodes single-crystal prompt, phases, bridged sub-models,
action verbs, or tab numbers — a new technique supplies all of it via its
manifest.

Next is **P2**: physically move the single-crystal code under
`techniques/single_crystal/` (one file per commit + re-export shims), driving
the technique-coupling ratchet to zero. The bind-surface contract test and
the manifest's lazy view imports keep those moves green at every commit.
