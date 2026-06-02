# Adding a new beamline plug-in

This guide walks through onboarding a new beamline into ExpHub. The goal is
that adding a beamline only requires creating a new directory under
`src/exphub/beamlines/<id>/` — no edits to `core/`, `app/`, or `agent/` code.

See `MULTI_BEAMLINE_PLAN.md` at the repo root for the design rationale.

> **Heads up:** A follow-on `MULTI_TECHNIQUE_PLAN.md` refactor is in
> progress. Once it lands, adding a beamline of a *different* technique
> family (e.g. SANS rather than single-crystal diffraction) requires
> declaring `technique="sans"` on the spec and using a different config
> shape; the per-beamline plug-in directory pattern itself stays the same.

---

## 1. Pick an id

Lowercase, no spaces, matches the package directory name. Examples in the
shipped plug-ins: `topaz`, `corelli`.

## 2. Create the directory skeleton

```
src/exphub/beamlines/<id>/
├── __init__.py          ← imports ``.spec`` so registration fires on import
├── spec.py              ← the BeamlineSpec instance + ``register()`` call
├── gonio.py             ← AMBIENT/CRYOGENIC/ANGLE_PVS, etc. (only if your
│                          beamline has goniometer-CSV import/export needs;
│                          otherwise omit)
├── screens/             ← optional Phoebus .bob / .macros for CSS Status tab
├── prompts/
│   └── context.md       ← per-beamline agent prompt fragment (~30-80 lines)
├── knowledge/           ← per-beamline RAG documents (Markdown)
│   └── *.md
└── tabs/                ← optional per-beamline tab content overrides
    └── css_status.py    ← typical first override; pure Vuetify3 layout
```

The minimum viable plug-in is `__init__.py` + `spec.py` + `prompts/context.md`.

## 3. Populate `spec.py`

Use [src/exphub/beamlines/corelli/spec.py](../src/exphub/beamlines/corelli/spec.py)
as a template. Required fields:
- `id`, `display_name`, `facility`, `target_station`
- `GoniometerSpec`: `angle_pvs`, `ramp_pvs`, `charge_pv`, `angle_columns_order`
- `DetectorSpec`: `extra_subscribe_pvs`, `monitor_pvs` (proton_charge / beam_power / wavelength)
- `MantidSpec`: `instrument_name` (the literal Mantid expects for `StartLiveData`)
- `PathsSpec`: `shared_root` (e.g. `/SNS/CORELLI`), `eic_dropbox`
- `EICSpec`: `beamline_code` (e.g. `bl9`), `run_title_pv`
- `AgentSpec`: `context_prompt`, `knowledge_dir`, at least one preset

Finish the file with `register(<MYBEAMLINE>)`. The registration is idempotent.

## 4. Hook the plug-in into discovery

Add an import to [src/exphub/beamlines/__init__.py](../src/exphub/beamlines/__init__.py):

```python
from . import <id>  # noqa: F401
```

Order matters for the *default* active beamline — the first-registered wins
when no explicit selection has been made.

## 5. Write the prompt fragment

`prompts/context.md` should be a 30-80 line Markdown block introducing the
beamline (wavelengths, sample environment, file-path conventions). It is
inserted between the agent's `core_identity.md` and the active task's
fragment when this beamline is active. Look at
[beamlines/topaz/prompts/context.md](../src/exphub/beamlines/topaz/prompts/context.md)
for a reference.

## 6. (Optional) Provide tab overrides

If your beamline needs a custom Instrument Status (CSS) tab — most do, since
the detector layout and PV names vary widely — drop a `tabs/css_status.py`
defining a class that takes a `MainViewModel` argument and lay it out with
Vuetify3 widgets. Then wire it through `BeamlineSpec.tabs`:

```python
def _build_css_status(view_model):
    from .tabs.css_status import CSSStatusView
    return CSSStatusView(view_model)

CORELLI = BeamlineSpec(
    ...,
    tabs=TabOverrides(css_status=_build_css_status),
)
```

The *lazy* factory pattern is required — eager imports of view code at
spec-construction time create circular dependencies through the gonio shim.

## 7. (Optional) Knowledge base

Drop Markdown files under `knowledge/`. The RAG indexer picks them up
automatically; ChromaDB persistence is keyed per beamline so switches don't
rebuild the index.

## 8. Verify

Run the tests:

```
pixi run python -m pytest tests/
```

The `tests/test_beamline_coupling.py` regression test asserts that no
TOPAZ/BL12 strings leak outside `beamlines/<id>/`. The
`tests/test_multi_beamline.py` suite covers registration, runtime switching,
and prompt composition.

For an interactive smoke check:

```python
import exphub.beamlines
from exphub.core.beamline import list_ids, set_active, active, BeamlineContext

print(list_ids())
spec = set_active("<your_id>")
ctx = BeamlineContext(spec)
print(ctx.angle_pv("omega"))
print(ctx.ipts_root(12345))
```

## 9. Notes

- The TOPAZ EIC integration assumes its `bl_12` dropbox layout; verify your
  beamline's EIC submission path before relying on `_copy_strategy_to_eic`.
- The vendored `app/models/eic_client.py` carries a hand-maintained
  beamline-id normalizer table — extending it for a new beamline is the only
  point that may need an edit outside `beamlines/<id>/`.
- The legacy `app/models/gonio_pvs.py` shim re-exports the active beamline's
  `gonio` module at import time. Callers that take the active beamline as a
  parameter (rather than via the shim) are preferred for new code.
