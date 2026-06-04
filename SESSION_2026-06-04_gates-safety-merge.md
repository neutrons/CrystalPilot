# CrystalPilot — Work Session Knowledge (2026-06-03 → 2026-06-04)

A durable record of what was done, **why**, the decisions made, and the
non-obvious knowledge/gotchas discovered. Forward-looking "what's next" lives in
[`HANDOFF.md`](HANDOFF.md) §6; this file is the "what happened + what we learned"
companion.

- **Branch:** `multibeamline` (ahead 145 / behind 0 of `origin/main`)
- **Final state:** **221 tests pass · `mypy .` 0 · `ruff check` + `ruff format` clean · technique-coupling ratchet `{}`** → the whole CI `build-and-test` job is green.
- **Env:** pixi, interpreter `.pixi/envs/default/bin/python`; Mantid 6.14.0 installed; nova-epics **0.3.1**.
- **Nothing pushed.** `main` (local + GitHub trunk) untouched at `1f49866`.

---

## 1. Commit map (this session)

| Commit | Item | What |
|---|---|---|
| `11282ee` | **A** | Drive `mypy .` 253 → **0**; add `tests/test_hygiene_ratchet.py` |
| `4c9b81d` | A | HANDOFF: record mypy=0; flag pre-existing ruff |
| `0f7f053` | **A** | `ruff check` 74 → 0 + `ruff format` (57 files) → CI fully green |
| `74d7503` | **B** | Behavioral fakes + golden-path tests; **fixes a latent EIC submit bug** |
| `0dc498d` | **C.1** | Code-level destructive-action confirmation gate |
| `17e548a` | **C.2** | Agent eval harness (deterministic, scripted LLM) |
| `2838a9e` | **D** | EIC client characterization tests (decomposition unblocked, deferred) |
| `f6f73ca` | **F** | Reword stale "residual"/"in-flight" ratchet comments |
| `ecdaeca`, `f9f5614` | docs | HANDOFF + memory updates |
| `c0ab182` | **E-adjacent** | Merge `origin/main` into `multibeamline` (nova-epics bump + PVPlot fix) |
| `462cb9d` | merge follow-up | Regenerate `pixi.lock` for nova-epics 0.3.1 |

Baseline before this session: commit `5830de0`, 180 tests, `mypy .` red (253), ruff red.

---

## 2. What was done, and why

### A — Make the quality gates bite ✅
- **mypy → 0.** `mypy .` (what CI runs) had **253 errors / 25 files**; the prior HANDOFF's "55" counted `mypy src` only — CI also flags ~198 `no-untyped-def` in tests/scripts. Fixed via a parallel Workflow (one agent per file) + a manual integration pass on **6 residuals the agents wrongly reported clean**. Real fixes: Optional guards/asserts for `MantidWorkflow | None` (temporal model + steering live loop) and `Agent | None` (chat VM); LangChain `str | list` message-content narrowing + `next_to_ask` in agent state; `type[BaseModel]` in `bridge`; canonical `api_key`/`base_url` in `llm`; dynamic `importlib` for optional `sentence_transformers`/`chromadb`; pyproject `ignore_missing_imports` for the optional `mcp` SDK; bulk `-> None`/fixture annotations.
- **Hygiene ratchet** (`tests/test_hygiene_ratchet.py`): caps `print(` in src/ (348), `type: ignore` (14), `# noqa` (34) across src+tests+scripts — ratchet-down-only, so the green mypy gate and the lint gate can't be quietly bypassed. Self-excludes its own file so it doesn't count its own pattern strings.
- **ruff → 0** (was pre-existing red, not from the mypy work). `ruff check --fix` for the mechanical ones; **scoped `per-file-ignores`** (not blanket suppression) for the legitimate cases — `tests/** → D101, N802` (test fakes mimic Mantid's camelCase `IPeak` API; test classes need no docstrings) and `selectors.py → E741, N806` (crystallographic notation: `h,k,l` Miller indices + `I` intensity). Then `ruff format` across 57 pre-existing non-compliant files.

### B — Behavioral fakes + golden-path tests ✅ (the biggest risk-reducer)
- `tests/conftest.py`: `FakeEICClient` (+ recording factory) and `FakeMantidWorkflow`, exposed as the `fake_eic` / `fake_mantid_workflow` fixtures.
- **EPICS needs no fake** — PVs are plain string constants passed to EIC as column names; real channel access lives only in the (untested) trame view layer (`main_view.py` via `nova.epics.trame`).
- Golden-path tests (one per technique): `tests/techniques/single_crystal/test_sc_golden_path_eic.py` (build angle plan → submit/poll/abort via fake EIC), `.../test_golden_path_temporal.py` (live-reduction *consumption* via the fake Mantid workflow — exercises the `assert wf is not None` paths from A), `tests/techniques/sans/test_sans_golden_path_eic.py` (SANS strategy → submit).
- **This work found and fixed a real latent bug** (see §3.1).

### C.1 — Code-level destructive-action confirmation gate ✅
- Replaced **prompt-only** safety ("confirm with the user first" in text) with a **code invariant**.
- `agent/confirmation.py::ConfirmationGate` (propose / confirm / cancel; one pending action at a time). `ActionTool.requires_confirmation` is set on `submit_angle_plan` + `stop_current_run`.
- A confirmation-required verb, when the LLM calls it, **only proposes** (records pending, returns `confirmation_required`); the destructive function runs **solely** from `handlers.handle_action_confirm` on an explicit user "yes" — run *first* in `run_handlers`, sticky until resolved. The chat VM owns the gate and shares it with the agent + handler chain. Defaults preserve old behavior (no gate / `requires_confirmation=False` → immediate). `tests/test_confirmation_gate.py` (16 tests) pins the invariant at the gate, tool, handler, and manifest layers.

### C.2 — Agent eval harness ✅
- `tests/test_agent_eval.py` runs `Agent.invoke` end-to-end through the **real LangGraph graph** with a **scripted LLM** (`ScriptedChatModel` + `scripted_agent_llm` fixture in conftest) — deterministic, no network/model. 4 golden conversations: set_parameter writes config; plain question passes through; **a destructive verb only proposes even when the model calls it** (C.1's invariant verified through the graph); a non-destructive verb executes.
- **Still TODO:** real-LLM tool-*selection* eval (offline, API-key-gated — out of scope for CI), and least-privilege tool scoping by phase.

### D — Decompose god-files ⚠️ UNBLOCKED, decomposition deferred
- B's golden-path tests **fake `EICClient` away**, so they gave **zero** coverage of the 1566-line `core/eic/eic_client.py`. Added `tests/test_eic_client_characterization.py` (9 tests) pinning its observable wire behavior with mocked `requests` on the non-auth path: construction (valid + invalid token), `submit_table_scan` (exact `/eic/actions` envelope + scan_id parsing), `get_scan_status`, `abort_scan`, `is_eic_enabled`.
- **Decomposition itself deferred on purpose:** this covers only the non-auth happy path; the **OAuth / SSL / platform / URL-derivation** paths still need characterization before that code is moved. Next: characterize the auth path, then extract `transport` / `auth` / `errors` into `core/eic/` submodules behind these tests. (Other god-files: `angle_plan_engine.py` 1161, `experiment_info.py` 1064, `angle_plan.py` 817, `steering.py` 738.)

### F — Loose ends
- ✅ Reworded the stale ratchet doc comments (BASELINE is `{}`, refactor complete).
- ⏭ **Needs a human:** CODEOWNERS placeholder handles (`@framework-team` etc. → real GitHub teams); provisional SANS/USANS values (SANS scientist / facility): strategy CSV columns, `iq_reduction` model (`"TBD"`, no real Mantid I(Q) pipeline), USANS spec (`eic.server_url`, real PVs `None`, placeholder STATUS/ANALYSIS).

### Merge of `origin/main`'s 2 commits into `multibeamline` ✅
Brought the 2 main-only commits into the branch (main untouched, nothing pushed):
`1f49866` (nova-epics `>=0.3.0` → `>=0.3.1`) and `707d888` (Fix PVPlot scaling for detector view).
- `pyproject.toml` auto-merged → nova-epics `>=0.3.1` (session's mypy/ruff config preserved).
- `pixi.lock` resolved `--ours` then **regenerated** via `pixi install` → nova-epics 0.3.1, **only that package changed** (no transitive churn).
- `css_status.py`: kept multibeamline's **`LogPVPlot`** redesign — `707d888`'s `scaling_pv_name` fix targeted the vendored `PVPlot` that this branch already replaced (LogPVPlot auto-scales from data + throttles render); `scaling_pv_name` isn't a `LogPVPlot` param. The other half of `707d888` (Total/Rate ROI labels) was already present, so nothing of value was dropped. **(This is the one judgment call worth a human glance.)**

---

## 3. Bugs & gotchas discovered (durable knowledge)

1. **EIC submit was silently broken for *every* technique.** `core/eic/control.py::_default_beamline_database()` reached into `.single_crystal.mantid.instrument_name` for *all* beamlines inside one dict-comp; once USANS was registered, `usans.single_crystal` raises `TypeError`, swallowed by a bare `except → return {}`. With an empty DB, `submit_jobs` set `supported_beamline=False` and bailed — for TOPAZ/CORELLI too. **Fixed** with a technique-neutral `BeamlineSpec.mantid_instrument_name` property + a per-beamline-resilient builder. (commit `74d7503`)
2. **`EICClient.__init__` raises `cryptography.fernet.InvalidToken` on a non-Fernet token** (including the default `token="test_password"`) — the `outer_fernet.decrypt(...)` call sits *outside* the handled try/except. Only masked today because every submit path is faked in tests. (found in `2838a9e`)
3. **`.mypy_cache` goes stale after bulk edits** → phantom "Module has no attribute X" / `import-not-found`. Always `rm -rf .mypy_cache` before trusting a full `mypy .` after large changes.
4. **Test files need globally-unique basenames.** `tests/` has no `__init__.py`, so pytest/mypy import test modules as top-level names — two files both named `test_golden_path_eic.py` caused an "import file mismatch" / "Duplicate module" error.
5. **EPICS isn't on the model/VM path** — only the trame view layer touches real channel access; PVs elsewhere are plain strings. No EPICS fake needed for behavioral tests.
6. **Mantid IS installed** (6.14.0) in the pixi env, so `MantidWorkflow` imports fine; the fake's job is to avoid live data streams, not import errors.
7. **Run the app as `python -m exphub.app`** (package is `exphub`, not `src.exphub`) or technique/beamline discovery breaks via a double-import. (pre-existing, see HANDOFF §2)

---

## 4. Branch landscape (as of 2026-06-04, live remote)

Live remote (`git ls-remote --heads origin`) has **4** branches: `main`, `multibeamline`, `agentize`, `hpc-demo`.

```
origin/main (1f49866)  ── trunk
  └── agentize (+52)         in-app LLM agent + live-data steering
        └── multibeamline    multi-beamline + multi-technique refactor + this session
                             (contains agentize; now ahead 145 / behind 0 of origin/main)
hpc-demo  ── ancient standalone HPC↔SNS demo (Nov 2025), abandoned, 53 behind
```

- **`multibeamline` fully contains `agentize`** (forked from agentize's tip). Once it lands, `agentize` is redundant.
- **`4-implement-instrument-status-page-with-webopidbwr` is a phantom**: deleted on GitHub (its instrument-status work merged to main) but still in the local remote-tracking cache. Clear it with `git fetch --prune`.
- The merge above made `multibeamline` "behind 0" — it now contains origin/main.

### ⚠️ Security finding (act on this)
The `origin` remote URL has a **GitHub Personal Access Token embedded in it** (`https://<user>:ghp_…@github.com/…`), stored plaintext in `.git/config`. **Rotate that PAT** and switch to a credential helper or SSH:
```
git remote set-url origin https://github.com/zhongcanxiao/CrystalPilot.git
```

---

## 5. How to verify everything is green
```bash
.pixi/envs/default/bin/python -m pytest -q                 # 221 passed
rm -rf .mypy_cache && .pixi/envs/default/bin/mypy .         # Success: no issues found
.pixi/envs/default/bin/ruff check                          # All checks passed!
.pixi/envs/default/bin/ruff format --check                 # all formatted
.pixi/envs/default/bin/python -c "import sys;sys.path.insert(0,'tests');import test_technique_coupling as t;print(t._scan())"   # {}
```

---

## 6. Open items / next (see HANDOFF.md §6 for detail)
- **Decompose `eic_client.py`** — now unblocked; characterize the OAuth/SSL path first, then split.
- **Least-privilege agent tool scoping** by task/phase; **real-LLM agent eval** (offline, API-key-gated).
- **Land `multibeamline` → main** — 145 commits ahead, CI-green, human-unreviewed. Decision deferred to the user (kept as local commits). Pull main's 2 commits is already done (this merge).
- **Human-needed:** rotate the PAT; real CODEOWNERS handles; confirm SANS/USANS provisional values; `git fetch --prune` the phantom branch.
- **Glance-worthy judgment call:** the `css_status.py` merge resolution (kept LogPVPlot over main's PVPlot scaling fix) — confirm that's the intended detector view.
