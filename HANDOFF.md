# CrystalPilot — Session Handoff (continue here)

**Last updated:** 2026-06-03 · **Branch:** `multibeamline` · **Tests:** 221 passing · **mypy:** 0 · **ruff:** green · **CI `build-and-test`:** fully green · **Technique-coupling ratchet:** 0

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
- ✅ **`mypy` is now 0 — DONE** (commit `11282ee`, `#5`). `mypy .` went **253 → 0**
  (the HANDOFF's "55 errors" counted `mypy src` only; CI runs `mypy .`, which
  also flags ~198 `no-untyped-def` in tests/scripts). The CI step is now green,
  so it bites. Fixes: Optional guards/asserts (`MantidWorkflow | None` in the
  temporal model + steering live loop, `Agent | None` in the chat VM), LangChain
  `str | list` message-content narrowing + `next_to_ask` in agent state,
  `type[BaseModel]` in `bridge`, canonical `api_key`/`base_url` in `llm`, dynamic
  `importlib` for optional `sentence_transformers`/`chromadb`, a pyproject
  `ignore_missing_imports` override for the optional `mcp` SDK (its names are
  used in annotations + `isinstance`), and bulk `-> None`/fixture annotations.
- ✅ **Hygiene ratchet added — DONE**: `tests/test_hygiene_ratchet.py` caps
  `print(` in `src/` (348) and `type: ignore` (14) / `# noqa` (31) across
  src+tests+scripts so the now-green mypy gate and the lint gate can't be quietly
  bypassed. **Ratchet down only** — lower a cap in the same commit when you
  delete debt; never raise one.
- ✅ **ruff green — DONE** (commit `0f7f053`, `#6`). `ruff check` 74→0 (scoped
  per-file-ignores for test fakes + crystallographic notation; real fixes
  elsewhere) and `ruff format` applied (57 files). The whole CI `build-and-test`
  job (ruff check + ruff format --check + mypy + pytest) is now green.

### B. Behavioral test fakes + golden path — ✅ **DONE** (commit `74d7503`, `#7`)
- `tests/conftest.py` adds `FakeEICClient` (+recording factory) and
  `FakeMantidWorkflow` as the `fake_eic` / `fake_mantid_workflow` fixtures.
  **EPICS needs no fake** — PVs are plain string constants passed to EIC as
  column names; real channel access lives only in the (untested) trame view layer.
- Golden-path tests: `tests/techniques/single_crystal/test_sc_golden_path_eic.py`
  (build angle plan → submit/poll/abort via fake EIC), `.../test_golden_path_temporal.py`
  (live-reduction consumption via the fake Mantid workflow),
  `tests/techniques/sans/test_sans_golden_path_eic.py` (SANS strategy → submit).
- **Bug found + fixed by these tests:** `_default_beamline_database()` collapsed
  to `{}` whenever a non-single-crystal beamline (USANS) was registered, so
  `submit_jobs` bailed (`supported_beamline=False`) for **every** technique.
  Fixed via a technique-neutral `BeamlineSpec.mantid_instrument_name` + a
  per-beamline-resilient builder.

### C. Harden the in-app agent — ✅ **C.1 + C.2 DONE** (commits `0dc498d`, `17e548a`)
- ✅ **C.1 code-level confirmation gate** (`agent/confirmation.py`
  `ConfirmationGate`): `ActionTool.requires_confirmation` (set on
  `submit_angle_plan` + `stop_current_run`); such a verb only *proposes* from a
  tool call; the destructive call runs only from an explicit user "yes" via
  `handlers.handle_action_confirm` (run first in `run_handlers`). The chat VM
  owns the gate. `tests/test_confirmation_gate.py` (16 tests).
- ✅ **C.2 agent eval harness** (`tests/test_agent_eval.py` +
  `ScriptedChatModel`/`scripted_agent_llm` in conftest): runs `Agent.invoke`
  end-to-end through the real graph with a scripted LLM (deterministic, no
  network). 4 golden conversations incl. the destructive-verb-can't-self-execute
  invariant. (Real-LLM tool-*selection* eval — gated on an API key, offline — is
  still TODO.)
- ⏭ Still TODO: least-privilege scoping of the agent's tool surface by task/phase.

### D. Decompose god-files — ⚠️ **UNBLOCKED, not yet done** (safety net added, commit `2838a9e`)
- `core/eic/eic_client.py` (**1566 lines**, priority), `angle_plan_engine.py`
  (1161), `experiment_info.py` (1064), `angle_plan.py` (817), `steering.py` (738).
- B's golden-path tests **fake `EICClient` away**, so they give zero coverage of
  eic_client.py. `tests/test_eic_client_characterization.py` (9 tests) now pins
  its wire behavior (submit/status/abort/ping request shape + response parsing,
  on the non-auth path). **The decomposition itself is deferred:** it covers the
  non-auth happy path only — characterize the **OAuth/SSL/platform/URL-derivation**
  paths *before* moving that code, then extract transport/auth/errors into
  `core/eic/` submodules behind the tests.
- **Gotcha surfaced:** `EICClient.__init__` decrypts the token *outside* the
  handled block, so a non-Fernet token (incl. the default `token="test_password"`)
  raises `InvalidToken` at construction — only masked today because submit paths
  are faked in tests.

### E. Land the branch — ⏭ **needs human sign-off** (outward-facing)
- `multibeamline` is **142 commits** ahead of `main` (185 files, +28.8k/−3.7k —
  the whole multi-beamline + multi-technique refactor), unreviewed-by-human,
  unpushed. Review → merge → tag. **Confirm with the user before pushing /
  opening a PR.**

### F. Loose ends / provisional items
- ✅ Reworded the stale "residual"/"in flight" ratchet doc comments (commit `f6f73ca`).
- ⏭ **CODEOWNERS handles are placeholders** (`@framework-team`,
  `@single-crystal-team`, `@sans-team`) — **needs a human** to supply real GitHub
  users/teams to activate review routing.
- ⏭ **SANS/USANS values are provisional** — **needs a SANS scientist / facility**:
  SANS strategy CSV columns (`sample_aperture`/`detector_distance`/`attenuator`/
  `wavelength_spread`); `iq_reduction` prediction model `"TBD"` (no real Mantid
  I(Q) pipeline); USANS spec (`eic.server_url`, real PVs `None`, placeholder
  STATUS/ANALYSIS tabs).

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

1. `git -C <repo> log --oneline -12` and `git status` to confirm you're on
   `multibeamline`, clean, at `f6f73ca` (or later).
2. `.pixi/envs/default/bin/python -m pytest -q` → expect **221 passed**.
3. Confirm all gates are green: technique-coupling
   `.pixi/envs/default/bin/python -c "import sys;sys.path.insert(0,'tests');import test_technique_coupling as t;print(t._scan())"`
   → `{}`; `.pixi/envs/default/bin/mypy .` → **Success**; `ruff check` →
   **All checks passed!**; `ruff format --check` → all formatted.
4. Pick an item from §6. **A, B, C.1, C.2, F are DONE; the whole CI job is now
   green.** Highest-leverage remaining: **§6D** (decompose `eic_client` — first
   characterize its OAuth/SSL path, then split, behind the new characterization
   tests) and **§6E** (land the branch — needs your sign-off). Keep the full
   suite + `mypy .` + `ruff` green per commit; **don't push without asking**.
