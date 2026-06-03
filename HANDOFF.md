# CrystalPilot — Session Handoff (continue here)

**Last updated:** 2026-06-03 · **Branch:** `multibeamline` · **Tests:** 180 passing · **Technique-coupling ratchet:** 0

This document is self-contained: read it top to bottom and you can continue the
work in a fresh session without re-deriving context. Canonical plan is
[`MULTI_TECHNIQUE_PLAN.md`](MULTI_TECHNIQUE_PLAN.md); parallel-dev rules are
[`docs/parallel_development.md`](docs/parallel_development.md).

---

## 1. What this project is

CrystalPilot (Python package name **`exphub`**) is a Nova-Trame (trame/Vue, MVVM)
web app for steering neutron-scattering beamline experiments at ORNL/SNS. It
talks to EPICS PVs (hardware), Mantid (reduction), and the EIC system (job
submission), and has a first-class LangGraph **LLM agent** that reads/writes the
same Pydantic models the UI does.

It has been refactored into a **plug-in architecture** so a new *technique
family* or *beamline* is added by dropping in files, never editing the
framework. Two techniques ship: **single_crystal** (beamlines TOPAZ, CORELLI)
and **sans** (beamline USANS / BL-1A).

---

## 2. How to work here (operational)

**Environment:** pixi. The interpreter is `.pixi/envs/default/bin/python`.

```bash
# Tests (full suite):
.pixi/envs/default/bin/python -m pytest -q          # or: pixi run pytest
# Just one lane:
.pixi/envs/default/bin/python -m pytest tests/techniques/single_crystal/ -q
# Lint / type:
.pixi/envs/default/bin/ruff check <files>           # or: pixi run ruff check
.pixi/envs/default/bin/mypy <files>                 # or: pixi run mypy .
# Run the app:
pixi run app                       # default beamline (TOPAZ)
pixi run app --beamline=usans      # or: CRYSTALPILOT_BEAMLINE=usans pixi run app
```

**Critical gotchas:**

- **Package name is `exphub`, not `src.exphub`.** The app MUST run as
  `python -m exphub.app` (the pixi `app` task does this). Running it as
  `src.exphub.app` loads a *second copy* of the package with separate module
  state → registry/technique discovery breaks silently. `main()` warns if
  launched under a non-canonical name.
- **`MainApp` uses the singleton trame server** — you can build it only **once
  per process**. To verify per-beamline construction, use a separate process
  each:
  ```bash
  for b in topaz corelli usans; do .pixi/envs/default/bin/python -c \
    "import exphub.beamlines; from exphub.core.beamline import set_active; set_active('$b'); \
     from exphub.app.views.main_view import MainApp; print('$b', bool(MainApp()))"; done
  ```

**Conventions:**

- Commit subject: short imperative (e.g. `#5: <what>`). **Never** add
  `Co-Authored-By` or any AI-attribution trailer (project rule).
- **Do not `git push` or open PRs** unless explicitly asked — local commits only.
- Keep edits surgical; match surrounding style. Read files before editing.
- `pixi run app` starts a server on :8080 — don't launch it from automation
  without a free port + `--server` + a timeout.

---

## 3. Architecture (mental model)

Four layers; dependencies point downward only (enforced — see §4):

```
app/        trame shell, MVVM wiring, manifest-driven tab dispatcher   (technique-agnostic)
agent/      LLM chat: schema/tools, phase machine, prompt composer, RAG
techniques/ experiment SHAPE per family: models, view-models, views, agent phases/verbs, prompts
  ├ single_crystal/   (UB, peaks, goniometer, angle plan, coverage)
  └ sans/             (I(Q), q-range — SKELETON/placeholder)
beamlines/  per-instrument params (PVs, paths) + tab overrides
  ├ topaz/  corelli/  → technique="single_crystal"
  └ usans/            → technique="sans"
core/       registries (beamline + technique), BeamlineSpec, paths, EIC pipeline (bottom layer)
```

**The contract = the `TechniqueManifest`** (`src/exphub/core/beamline/technique.py`).
It is the API a technique exposes to the shell + agent:
`default_tabs`, `tab_override_slots`, `bridged_submodels`, `field_owner`,
`phases`, `action_tools`, `tab_labels`/`tab_aliases`, `prompts_dir`,
`eic_row_builder`, `root_model_factory`, `steering_vm_factory`. Behind it a
technique can change anything.

**Composition seam** (`app/mvvm_factory.py`): builds the active technique's root
model via `active_technique().root_model_factory` and its steering VM via
`steering_vm_factory`. Each technique supplies a root model:
`techniques/single_crystal/models/root.py::SingleCrystalMainModel` and
`techniques/sans/models/root.py::SansMainModel`. The app no longer names any
technique class except as TYPE_CHECKING hints / a lazy fallback.

**Trame bind namespaces** (the view↔VM string API):
- `controls` → app-shell view-state (active_tab, beamline selector, dialogs)
- `steering` → single-crystal steering view-state (hkl menus, is_live_update_running)
- `config`, `model_angleplan`, `model_eiccontrol`, `model_temporalanalysis`,
  `model_dataanalysis`, `model_cssstatus`, `model_newtabtemplate` → sub-models
- These are pinned by `tests/test_viewmodel_surface.py` (don't rename without
  updating it).

**Key files:**
- `app/main.py` — entry + startup beamline selector
- `app/views/main_view.py` — `MainApp` (server, title, EPICS connect)
- `app/views/tab_content_panel.py` — manifest-driven 5-slot dispatcher
- `app/mvvm_factory.py` — builds shell VM + technique steering VM + chat VM
- `app/view_models/app_shell.py` — `AppShellViewModel` (nav, selector, snackbar, dialogs)
- `app/view_models/chat.py` — `ChatViewModel` (agent lifecycle, config apply)
- `core/beamline/{spec,registry,context,technique}.py` — the framework
- `core/eic/{eic_client,control,row_builder}.py` — EIC pipeline
- `techniques/single_crystal/view_models/steering.py` — `SingleCrystalSteeringViewModel` (~45 methods)
- `agent/{agent,tools,bridge,workflow,rag}.py` — agent runtime

---

## 4. Invariants / guardrails (run + keep green)

These are executable contracts. **The full suite must stay green at every
commit.** The most load-bearing:

| Test | Protects |
|---|---|
| `tests/test_technique_coupling.py` | **Ratchet = 0.** No single-crystal vocabulary in `app/` or `core/`. `BASELINE={}`. Must stay 0. |
| `tests/test_import_boundaries.py` | single_crystal ⊥ sans; core imports nothing upward; techniques ⊥ app; beamlines mutually independent. |
| `tests/test_beamline_coupling.py` | No hardcoded TOPAZ/BL12 ids in framework code. |
| `tests/test_viewmodel_surface.py` | The view↔VM trame bind names (steering VM + shell VM). |
| `tests/test_tab_overrides.py` | The 5-slot dispatcher fall-through, for TOPAZ + CORELLI. |
| `tests/test_app.py` | `MainApp()` constructs. |
| `tests/test_acceptance.py` | End-state: ratchet residual `{}`, ships both techniques + 3 beamlines. |

Lane tests live in `tests/techniques/{single_crystal,sans}/`; shared
contract/integration tests stay at `tests/` root. `.github/CODEOWNERS` maps the
ownership (placeholder handles — see §6).

---

## 5. What's been done (condensed history)

- **Multi-beamline refactor** (prior): per-instrument *parameters* became plug-in
  (PVs, paths, screens, presets, prompts). Coupling 235→0. TOPAZ + CORELLI ship.
- **Multi-technique refactor P0–P6** (`MULTI_TECHNIQUE_PLAN.md`): lifted the
  implicit single-crystal *shape* out of `app/`/`core/`.
  - P0/P0.5/P1: ratchet test, discriminated-union `BeamlineSpec`, `TechniqueManifest`,
    agent parametrised (phases/prompts/bridged-submodels/action-tools from manifest).
  - P2: moved all single-crystal models/views/view-models into
    `techniques/single_crystal/`; split `MainViewModel` →
    `AppShellViewModel` (app) + `SingleCrystalSteeringViewModel` (technique).
  - P3–P6 (done by an **autonomous overnight agent workflow**, 16 commits
    `edb0493..2851ccf`): manifest-driven dispatcher + `PlaceholderTab` +
    cross-technique selector gating + `on_deactivate`; EIC decomposed into
    `core/eic/` + per-technique `EICRowBuilder`; **SANS technique skeleton**;
    **USANS beamline plug-in**; docs + acceptance test.
    Log: `docs/sessions/SESSION_2026-06-03-multitechnique-overnight.md`.
- **Startup beamline selector** (`9d4c632`) + **launch-as-`exphub.app` fix**
  (`a88da60`) — see §2 gotchas.
- **Parallel-dev foundation** (`d7b2bfe`, `e0b0e7c`, `d89f618`, `29ed210`, `208a76f`):
  - #1: `MainModel` → `techniques/single_crystal/models/root.py`
    (`SingleCrystalMainModel`); `TabOverrides` slots neutral
    (`ipts/live/steering/status/analysis`); **ratchet 6 → 0**.
  - #2: `tests/test_import_boundaries.py` + `.github/CODEOWNERS`.
  - #3: `tests/techniques/<id>/` lane homes.
  - #4: `docs/parallel_development.md`.

---

## 6. What's NEXT (prioritized — this is the job to continue)

Ordered by leverage. Each is independent enough to do in its own session.

### A. Make the quality gates bite (cheap, high value)
- **Drive `mypy` to 0, then make it CI-blocking.** Today: **55 errors / 13 files**
  (`mypy .` is already a CI step, so it's red-and-ignored). Most are
  `union-attr` — `Optional` values dereferenced without a guard (latent
  `None`-crashes), e.g. `SingleCrystalSteeringViewModel._live_update_task` /
  `MantidWorkflow | None`. Also 1 `no-untyped-def` in `beamlines/topaz/spec.py`,
  `D101` in `EICSpec`, etc. Fix them, then add a "no new `print` / no new
  `# noqa` / no new `type: ignore`" ratchet (same pattern as
  `test_technique_coupling`). There are currently **348 `print(`** calls and
  10 `type: ignore`.

### B. Behavioral test fakes + golden path (the biggest risk-reducer)
- The suite is structural ("constructs", "ratchet", "golden rows"); the actual
  science workflows (live Mantid reduction, coverage optimization, EIC
  submission, EPICS reads) are largely **un-tested end-to-end**. Build **fakes**
  for the three hard deps (a fake EIC server, recorded Mantid workspaces, a fake
  EPICS PV source) and write **one golden-path integration test per technique**
  (load IPTS → build strategy → submit → observe). This is the safety net that
  lets agents + humans refactor the god-files (§D) without fear.

### C. Harden the in-app agent (high consequence — it steers real hardware)
- **Replace prompt-only safety with code gates.** Destructive actions
  (`stop_current_run` aborts a running scan; `submit_angle_plan`) are guarded
  only by *text* in the `ActionTool.description` ("confirm with the user before
  calling it"). Implement a typed **propose → user-confirms → execute** gate the
  model cannot bypass. (Manifest `action_tools` live in
  `techniques/single_crystal/manifest.py`; 5 verbs today.)
- **Agent eval harness:** golden conversations → expected tool-calls / parameter
  writes, run in CI, so prompt/model/schema changes can't silently regress the
  agent.
- Consider least-privilege scoping of the agent's tool surface by task/phase.

### D. Decompose god-files (do AFTER B exists)
- `core/eic/eic_client.py` (**1566 lines**), `angle_plan_engine.py` (1161),
  `experiment_info.py` (1064), `angle_plan.py` (817), `steering.py` (738).
  `eic_client` is the priority but is risky (auth/submit) — only refactor it
  behind the behavioral tests from §B.

### E. Land the branch
- `multibeamline` is ~30 commits ahead of `main`, unreviewed-by-human, unpushed.
  Review → merge → tag. Don't let it become a parallel universe. (This is
  outward-facing — **confirm with the user before pushing / opening a PR.**)

### F. Loose ends / provisional items
- **CODEOWNERS handles are placeholders** (`@framework-team`,
  `@single-crystal-team`, `@sans-team`) — replace with real GitHub users/teams to
  activate review routing.
- **SANS/USANS values are provisional** (skeleton; ships gated, works, but not
  behaviorally complete) — need SANS scientist / facility confirmation:
  - SANS strategy CSV columns (`sample_aperture`, `detector_distance`,
    `attenuator`, `wavelength_spread`).
  - `iq_reduction` prediction model = `"TBD"` (no real Mantid I(Q) pipeline).
  - USANS spec: `eic.server_url="https://eic.sns.gov"`, real PVs `None`,
    placeholder STATUS/ANALYSIS tabs.
- Minor: a couple of doc comments in `test_technique_coupling.py` still talk
  about a "residual" — now zero; reword when convenient.

---

## 7. Pointers

- [`MULTI_TECHNIQUE_PLAN.md`](MULTI_TECHNIQUE_PLAN.md) — canonical plan (incl. the
  deferred **P3a-future**: true live cross-technique hot-swap; v1 requires restart).
- [`MULTI_BEAMLINE_PLAN.md`](MULTI_BEAMLINE_PLAN.md) — predecessor refactor.
- [`docs/parallel_development.md`](docs/parallel_development.md) — lane rules, branching.
- [`docs/architecture/`](docs/architecture/) — one page per layer.
- [`docs/adding_a_technique.md`](docs/adding_a_technique.md) /
  [`docs/adding_a_beamline.md`](docs/adding_a_beamline.md) — onboarding.
- [`docs/sessions/`](docs/sessions/) — session logs (latest:
  `SESSION_2026-06-03-multitechnique-overnight.md`).
- Auto-memory index: `~/.claude/projects/.../memory/MEMORY.md` (project state,
  conventions, the no-attribution commit rule).

## 8. First moves in a new session

1. `git -C <repo> log --oneline -8` and `git status` to confirm you're on
   `multibeamline`, clean, at `208a76f` (or later).
2. `.pixi/envs/default/bin/python -m pytest -q` → expect **180 passed**.
3. Confirm the ratchet is still 0:
   `.pixi/envs/default/bin/python -c "import sys;sys.path.insert(0,'tests');import test_technique_coupling as t;print(t._scan())"`
   → `{}`.
4. Pick an item from §6 (suggested order: A → B → C). Keep the full suite green
   per commit; don't push without asking.
