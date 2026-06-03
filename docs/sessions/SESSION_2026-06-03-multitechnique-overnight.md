# Session 2026-06-03: Multi-Technique Refactor — Overnight Autonomous Run (P3–P6)

**Update for the user (read first):** Overnight P3→P6 ran clean. All phases landed and verified green — suite is now **170 passed**, technique-coupling ratchet down to **6** (the documented `main_model.py`=4 + `core/beamline/spec.py`=2 residual, deferred to a later phase), and an acceptance test now pins that residual so it can't silently grow. SANS technique skeleton + USANS (BL-1A) beamline plug-in are in, gated cross-technique switching works, and onboarding/architecture docs are written. Nothing is broken; no pushes. Provisional SANS placeholders (CSV columns, `iq_reduction`="TBD") remain to be confirmed with the SANS scientist.

Branch: `multibeamline`. No push, no PRs, no new branches — all commits local.
Plan: [`MULTI_TECHNIQUE_PLAN.md`](../../MULTI_TECHNIQUE_PLAN.md).
Predecessor: [`SESSION_2026-06-02-multitechnique-P2.md`](SESSION_2026-06-02-multitechnique-P2.md).
Ratchet: `tests/test_technique_coupling.py` (`INITIAL_CAP` = 6 by end of run).

## Summary

| Phase | What | Status | Suite | Ratchet |
|-------|------|--------|-------|---------|
| P3   | Manifest-driven tab dispatcher + gated cross-technique selector + CORELLI data-analysis tab | ✅ green | 152 passed | 26 |
| P3a  | EIC decomposition — single-crystal CSV row logic into `eic_row_builder` seam; `eic_control` coupling zeroed | ✅ green | 157 passed | 6 |
| P4   | SANS technique skeleton (purely additive package) | ✅ green | 163 passed | 6 |
| P5   | USANS (BL-1A) beamline plug-in | ✅ green | 164 passed | 6 |
| P6   | Onboarding + architecture docs; acceptance checks pinning the residual | ✅ green | 170 passed | 6 |

Stopped-at phase: **none** — all planned phases (P3, P3a, P4, P5, P6) were attempted and each verified green. No resume needed.

Every phase was verified against the four gates: full suite green, `test_app.py` (MainApp constructs), the technique-coupling ratchet (no BASELINE raised), and ruff+mypy with zero *new* findings on changed files.

## Phase P3 — manifest-driven tab dispatcher

Commits: `edb0493` (manifest-driven tab dispatcher + `PlaceholderTab`), `1f7deb6` (gate cross-technique selector + steering `on_deactivate`), `7e7fe27` (CORELLI data-analysis tab), `55fde27` (annotate CORELLI factory), `e045743` (fix 9 new ruff nits P3 introduced in `test_tab_overrides.py`).

- `TabContentPanel` now resolves all 5 tab slots through a manifest fall-through: override → technique default → opted-in optional → `PlaceholderTab`. No technique imports remain in `tab_content_panel.py` (fully manifest-driven).
- Cross-technique selector option is disabled; steering view-model gains `on_deactivate` for the restart-gated switch.
- CORELLI gets a real data-analysis tab (tab 6, `TabKey.ANALYSIS`) wired to `corelli.tabs.data_analysis` (the real `DataAnalysisView` factory bound to `model_dataanalysis`, not the placeholder).
- Suite: **152 passed**, 4 pre-existing deprecation warnings.
- Ratchet total **26** = `eic_control.py`=20 + `main_model.py`=4 + `core/beamline/spec.py`=2 (the 3 BASELINE rows). P3.1 removed the `tab_content_panel.py` BASELINE row (file now at 0 SC tokens). No BASELINE raised.
- ruff/mypy: 0 new mypy errors; the 9 new ruff nits (4×D205, 3×D209, 2×I001 in the new test fns) were fixed in `e045743`. All remaining findings pre-existing.

## Phase P3a — EIC decomposition (ratchet drops to 6)

Commits: `8d3b5c9`, `160189e`, `434735c`.

- The inline angle-plan CSV row logic that lived in `EICControlModel.submit_eic` was lifted into `SingleCrystalEICRowBuilder.build_jobs` (`techniques/single_crystal/agent/eic_row_builder.py`). `core/eic/control.py::submit_jobs` submits the identical payload `{"run_mode":0,"headers":headers,"rows":[row]}`.
- **Behavior-preserving** — independently rebuilt TOPAZ/CORELLI jobs over a 3-row plan (PCharge-wait angle, Time-wait angle, ramp); output byte-identical to the golden `_TOPAZ_JOBS`/`_CORELLI_JOBS` in `test_eic_row_builder.py` (same PV columns `BL12:Mot:goniokm:*` / `BL9:Mot:Sample:*`, same PCharge→`BL*:Det:PCharge:C` mapping, same ramp layout/metadata).
- Suite: **157 passed**.
- Ratchet total **6** = `main_model.py`=4 + `core/beamline/spec.py`=2. `eic_control` coupling zeroed and its BASELINE row removed; cap tightened from 26 → 6.
- ruff/mypy: 0 new findings (9 ruff + 7 mypy all verified pre-existing at `8d3b5c9^`).

**Doc-vs-aspiration mismatch (non-blocking):** the ratchet module's comments aspirationally say the count "reaches 0 at the end of P3a", but two files legitimately remain at total 6, deferred to a later phase per the in-test comment. Tests pass and the cap is correct; this is purely a comment that should be reworded later.

## Phase P4 — SANS technique skeleton (additive)

Commits: `0b3cf30` (models skeleton), `c65a15d` (view-models + tab views), `5f502da` (manifest, phases, prompts, row-builder), `027ddab` (end-to-end tests).

- New package `src/exphub/techniques/sans/`: `manifest.py`, `models/{ipts_info,strategy,iq_reduction,root}.py`, `view_models/steering.py`, `views/{ipts_info,strategy,iq_reduction}.py`, `agent/{phases,eic_row_builder}.py`, `prompts/context.md`.
- `test_multi_technique.py` (6 passed) confirms: single-crystal tab1 model has `crystalsystem`, SANS tab1 does not; techniques differ on the same slot; cross-technique selector option disabled; cross-technique switch refused with banner; same-technique switch not gated.
- Suite: **163 passed**. Ratchet unchanged at **6** — SANS added **zero** framework-side single-crystal coupling (no SANS file appears in the scan).
- ruff: clean on all 17 changed files. mypy: clean on all 16 SANS source modules. The pre-existing `steering.py`/`topaz/spec.py` errors surfaced via import-following were verified pre-existing on the pre-P4 baseline; the new test file follows the repo's established un-annotated-test convention.

## Phase P5 — USANS (BL-1A) beamline plug-in

Commit: `0b98ea2`.

- New plug-in `src/exphub/beamlines/usans/` (spec, prompts, knowledge). Registry now registers `['corelli','topaz','usans']`. `set_active('usans')` → `id='usans'`, `technique='sans'`, `eic.beamline_code='bl1a'`, `eic.server_url='https://eic.sns.gov'`, `paths.shared_root='/SNS/USANS'`, `technique_config.kind='sans'`, `mantid_instrument_name='USANS'`.
- `MainApp()` constructs end-to-end under the SANS technique with USANS active (`test_mainapp_constructs_with_usans_active`). P4's in-test stub spec was removed — the test now uses the real registered plug-in.
- Suite: **164 passed**. Ratchet unchanged at **6** (USANS adds no SC coupling).
- ruff: clean except one **pre-existing** `I001` on `beamlines/__init__.py` (intentional non-alphabetical registration order, documented in-file; verified identical at `027ddab`). mypy: clean on changed source files.

## Phase P6 — docs + acceptance checks

Commits: `f76d08b` (technique/beamline onboarding + architecture docs), `2851ccf` (acceptance checks).

- Docs: `docs/adding_a_technique.md`, `docs/adding_a_beamline.md`, `docs/architecture/`.
- `tests/test_acceptance.py` (6 passed) pins the residual explicitly:
  - `test_single_crystal_coupling_matches_documented_residual` asserts `_scan()` == `{"...main_model.py": 4, "...core/beamline/spec.py": 2}` (same scanner + PATTERN as the ratchet).
  - `test_acceptance_residual_tracks_ratchet_baseline` asserts `EXPECTED_RESIDUAL == BASELINE` so the two can never disagree.
  - Structural: ships `single_crystal` + `sans` techniques (self-id); ships `topaz`+`corelli`+`usans` beamlines (topaz/corelli→single_crystal, usans→sans).
- Suite: **170 passed**. Ratchet **6**.
- ruff/mypy clean on changed files (same pre-existing `beamlines/__init__.py` I001 noted above).

## Final state

- **170 passed**, 4 warnings (pre-existing `pkg_resources` + Pydantic-v2 class-based-config deprecations only). Working tree clean; HEAD at `2851ccf`.
- Technique-coupling ratchet: **6**, `INITIAL_CAP = 6`, BASELINE = `{main_model.py: 4, core/beamline/spec.py: 2}`.

## Deferred / TODO / provisional

- **Ratchet residual (6) not yet zeroed.** `main_model.py` (4) and `core/beamline/spec.py` (2) still carry single-crystal tokens — the `root_model_factory` + `TabOverrides` reshape is scheduled for a later phase. Now pinned by `test_acceptance.py` so it can't grow silently.
- **Ratchet comment wording.** `test_technique_coupling.py` comments say the count hits 0 at end of P3a; reality is 6. Reword (non-blocking).
- **SANS provisional placeholders (confirm with SANS scientist):**
  - Strategy CSV uses TOPAZ-shaped rows with SANS placeholder columns (`sample_aperture`, `detector_distance`, `attenuator`, `wavelength_spread`) — marked "column names provisional (TBD with SANS scientist)".
  - `iq_reduction` model = placeholder dropdown value `"TBD"`; no real Mantid I(Q) pipeline.
- **USANS spec provisional values** (documented inline in `spec.py`): `eic.server_url='https://eic.sns.gov'`, unknown real PVs → `None`, empty eic_dropbox; placeholder STATUS/ANALYSIS tabs with generic message + Mantid/SNS links.
- **Pre-existing lint/type debt (not introduced this run):** `steering.py` (6× union-attr on `MantidWorkflow | None`, 4× E402, 1× F841, 1× D205), `topaz/spec.py` (1 no-untyped-def), `spec.py` D101, `beamlines/__init__.py` I001, test-file `N806`/`no-untyped-def` per repo convention.

## Relevant files

- `src/exphub/app/views/tab_content_panel.py`, `src/exphub/app/views/placeholder_tab.py`
- `src/exphub/beamlines/corelli/tabs/data_analysis.py`
- `src/exphub/techniques/single_crystal/agent/eic_row_builder.py`, `src/exphub/core/eic/{control,row_builder}.py`
- `src/exphub/techniques/sans/` (full new package)
- `src/exphub/beamlines/usans/spec.py`, `src/exphub/beamlines/__init__.py`
- `tests/test_technique_coupling.py`, `tests/test_acceptance.py`, `tests/test_multi_technique.py`, `tests/test_tab_overrides.py`, `tests/test_eic_row_builder.py`
- `docs/adding_a_technique.md`, `docs/adding_a_beamline.md`, `docs/architecture/`
