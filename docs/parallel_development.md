# Developing techniques in parallel (TOPAZ ↔ USANS)

How two technique lanes — single-crystal (TOPAZ, CORELLI) and SANS (USANS) —
are developed at the same time, in one repo, without stepping on each other.

The short version: **stable contract + isolated implementations +
CI-enforced boundaries.** Stay in your lane and the other lane never sees your
changes; the only place the two lanes meet is a deliberate, reviewed change to
the manifest contract or the shared trunk.

## The three lanes

| Lane | Directories | Who changes it |
|---|---|---|
| **Single-crystal** | `src/exphub/techniques/single_crystal/`, `src/exphub/beamlines/topaz/`, `src/exphub/beamlines/corelli/`, `tests/techniques/single_crystal/` | TOPAZ/CORELLI owner — **no coordination needed** |
| **SANS** | `src/exphub/techniques/sans/`, `src/exphub/beamlines/usans/`, `tests/techniques/sans/` | USANS owner — **no coordination needed** |
| **Trunk (shared)** | `src/exphub/core/`, `src/exphub/app/`, `src/exphub/agent/`, the shared contract tests | **Coordinate** — framework review |

Because the lanes are disjoint *files*, two people rewriting their own
models/views/view-models **cannot produce a merge conflict**. The only conflict
surface is the trunk, so the whole strategy is: keep work in the lanes, and make
trunk changes rare, small, and reviewed.

## What enforces the boundary (so it isn't just discipline)

These run in CI and fail the build on violation:

- **`tests/test_import_boundaries.py`** — single-crystal and SANS may not import
  each other; `core/` imports no upper layer; techniques never import `app/`;
  beamline plug-ins are mutually independent. This is the structural guarantee
  that churn in one lane cannot reach the other.
- **`tests/test_technique_coupling.py`** (ratchet, now at **0**) — no
  single-crystal vocabulary may appear in `app/` or `core/`. The shared trunk
  stays technique-neutral, so a SANS dev can trust it.
- **`tests/test_beamline_coupling.py`** — no hardcoded beamline ids in framework
  code.
- **`tests/test_viewmodel_surface.py`** — pins the view↔view-model trame bind
  names, so a heavy view/VM refactor that renames a bind fails here first
  (update it in the same PR).
- **`.github/CODEOWNERS`** — maps each lane (and its tests) to its owner and the
  trunk to framework review, so the social boundary matches the code boundary.

## The contract between a technique and the app

`TechniqueManifest` (`src/exphub/core/beamline/technique.py`) **is** the API a
technique exposes to the shell and the agent:

`default_tabs`, `tab_override_slots`, `bridged_submodels`, `field_owner`,
`phases`, `action_tools`, `tab_labels`/`tab_aliases`, `prompts_dir`,
`eic_row_builder`, `root_model_factory`, `steering_vm_factory`.

Behind the manifest you can rewrite anything. "Change lots of models/views/VMs
for TOPAZ" is safe **as long as the manifest surface is honored**. A change that
alters what the manifest exposes (a new `bridged_submodel`, a new `action_tool`,
a changed factory) is the *one* shared touch — keep it additive, and it's
reviewed as an API change.

## Branching model: trunk-based, not branch-per-technique

Do **not** keep one long-lived "TOPAZ" branch and one "USANS" branch. They won't
conflict on the lanes — they'll conflict (painfully) on the *trunk* after months
of drift.

Instead:

- **Short-lived branches, merged often.** Lane changes merge freely; trunk
  changes are small and framework-reviewed.
- **An incomplete technique just ships, gated.** A technique is isolated and
  restart-gated, so a half-built SANS coexists in the same shipped app as a
  finished TOPAZ — placeholder tabs, no breakage. You do **not** need a fork or
  a long branch to develop USANS "in parallel"; you develop it on the main line
  behind its existing gate. (Launch it with `pixi run app --beamline=usans`.)

## Workflow: heavily reworking a single-crystal tab

1. Edit only under `techniques/single_crystal/{models,view_models,views}/`
   (plus `beamlines/topaz/` if it's a beamline override). The SANS dev sees
   nothing — different files.
2. If the rework changes what the tab exposes to the app/agent (a new
   `bridged_submodel`, `action_tool`, or factory), that's the **one** shared
   touch — a manifest change, kept additive and reviewed as such.
3. Run your lane: `pixi run pytest tests/techniques/single_crystal/`.
4. The shared gate must stay green: `pixi run pytest` (especially `test_app`,
   `test_import_boundaries`, the ratchets, `test_viewmodel_surface`). That's the
   proof you didn't break the contract. Merge.

USANS work proceeds untouched the entire time.

## Changing a shared contract (the trunk)

When the framework genuinely must change in a way that affects both techniques
(a new required manifest field, a `TabKey` change), use **expand → migrate →
contract**:

1. **Expand** — add the new capability as optional/additive; old path still works.
2. **Migrate** — update each technique (and beamline) to the new capability,
   one lane at a time.
3. **Contract** — remove the old path once both lanes are migrated.

Never a flag-day that breaks both techniques at once.

## Quick checklist (per change)

- [ ] Does it stay inside one lane? → no coordination needed; run that lane's tests.
- [ ] Does it touch `core/`/`app/`/`agent/` or the manifest? → trunk change, framework review, prefer additive.
- [ ] `pixi run pytest` green (the integration gate)?
- [ ] `ruff check` / `mypy` clean on changed files?
- [ ] Import boundaries + coupling ratchets still green (automatic in the suite)?

See also: [`adding_a_technique.md`](adding_a_technique.md),
[`adding_a_beamline.md`](adding_a_beamline.md),
[`architecture/`](architecture/).
