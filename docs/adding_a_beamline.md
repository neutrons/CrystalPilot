# Adding a new beamline plug-in

A *beamline* is one physical instrument. It plugs into exactly one *technique
family* and supplies only **per-instrument** values — EPICS PVs, file-system
roots, the EIC server, agent context — plus optional per-tab overrides. The tab
shapes, data model, agent phases, and action verbs all come from the technique
manifest, so adding a beamline means dropping a directory into
`src/exphub/beamlines/<id>/` with **no edits to `core/`, `app/`, or `agent/`**.

ExpHub ships `topaz`, `corelli` (technique `single_crystal`) and `usans`
(technique `sans`). See [architecture/beamlines.md](architecture/beamlines.md)
for the one-page map and `MULTI_TECHNIQUE_PLAN.md` for the design rationale.

---

## First: is this even a new beamline?

```
                    Do you need a new instrument's
                       PVs / paths / EIC server?
                                  |
                    +-------------+-------------+
                   no                           yes
                    |                            |
        Editing tab content,         Is it the SAME kind of
        data model, agent             experiment as a shipped
        phases/verbs?                 technique (single_crystal
                    |                  or sans)?
            +-------+------+              |
        view only      model/agent   +----+----------------+
            |          /workflow     yes                   no
   per-beamline tab        |          |                    |
   OVERRIDE (this doc,  NEW TECHNIQUE  NEW BEAMLINE of      NEW TECHNIQUE
   step 6)             (adding_a_       an existing         first, then a
                       technique.md)    technique           beamline of it
                                        (THIS DOC)          (adding_a_
                                                            technique.md)
```

Worked decision: **GP-SANS at HFIR** does the same kind of experiment as USANS
(both `technique="sans"`). It is therefore a **new beamline of the existing
`sans` technique** — exactly the case this guide walks through. It needs new
PVs, paths, and an EIC server, but reuses the SANS tabs, model, phases, and
verbs unchanged. If instead you needed reflectometry (a different experiment),
you would first read [adding_a_technique.md](adding_a_technique.md).

---

## 1. Pick an id

Lowercase, no spaces, matches the package directory name. Shipped examples:
`topaz`, `corelli`, `usans`. We use `gpsans`.

## 2. Create the directory skeleton

```
src/exphub/beamlines/gpsans/
├── __init__.py          imports .spec so register() fires on import
├── spec.py              the BeamlineSpec instance + register(GPSANS)
├── prompts/
│   └── context.md       per-beamline agent prompt fragment (~30-80 lines)
├── knowledge/           per-beamline RAG documents (Markdown)
│   └── *.md
└── tabs/                optional per-beamline tab overrides (e.g. css_status.py)
```

The minimum viable plug-in is `__init__.py` + `spec.py` + `prompts/context.md`.
Single-crystal beamlines also ship a `gonio.py` (goniometer PV tables) and a
`screens/` `.bob` operator screen; SANS beamlines like GP-SANS usually do not.

`__init__.py` just imports the spec so registration fires:

```python
"""GP-SANS (HFIR CG-2) beamline plug-in."""
from .spec import GPSANS  # noqa: F401 — registers on import
__all__ = ["GPSANS"]
```

## 3. Populate `spec.py` — GP-SANS worked example

Use `beamlines/usans/spec.py` as the template (it is the other `sans` beamline).
The `technique_config` discriminator (`SansConfig`) is what selects the SANS
technique; the validator copies its `kind` onto `spec.technique` for you.

```python
from pathlib import Path
from ...core.beamline import (
    AgentSpec, BeamlineSpec, DetectorSpec, EICSpec, PathsSpec,
    SansConfig, TabKey, register,
)

GPSANS = BeamlineSpec(
    id="gpsans",
    display_name="GP-SANS (CG-2)",
    facility="HFIR",
    target_station="HB-CG2",
    technique="sans",                       # derived from technique_config.kind
    detector=DetectorSpec(
        detector_layout="gpsans_area",       # GP-SANS has a real area detector
        pixel_dims=(192, 256),               # provisional — confirm with CG-2 scientist
        monitor_pvs={},                       # fill from the CG-2 PV catalog
    ),
    paths=PathsSpec(
        shared_root="/HFIR/CG2",
        eic_dropbox="",                       # set if GP-SANS uses dropbox submit
    ),
    eic=EICSpec(
        beamline_code="cg2",
        is_simulation_default=False,
        server_url="https://eic.hfir.gov",    # provisional — real CG-2 EIC TBD
    ),
    technique_config=SansConfig(
        mantid_instrument_name="GPSANS",
        default_q_range=None,                 # fill when the reduction spec lands
        transmission_monitor_pv=None,
        live_stream_url=None,
    ),
    agent=AgentSpec(
        context_prompt=Path("prompts/context.md"),
        knowledge_dir=Path("knowledge"),
        presets={},
        supported_tasks=["experiment_steering", "app_help"],
    ),
    # The SANS technique has no STATUS/ANALYSIS default, so supply placeholders
    # until real tabs exist (same pattern USANS uses).
    placeholder_messages={
        TabKey.STATUS: "Instrument Status is not yet wired for GP-SANS (CG-2).",
        TabKey.ANALYSIS: "Reduce GP-SANS data in MantidWorkbench (HFIR-SANS).",
    },
    placeholder_links={
        TabKey.ANALYSIS: [("MantidWorkbench", "https://www.mantidproject.org/")],
    },
)

register(GPSANS)
```

That is the whole beamline. The SANS manifest supplies the three default tabs
(IPTS Info, I(Q) Reduction, Strategy), the root model, the steering VM, the
agent phases, and the action verbs — GP-SANS re-declares none of it.

## 4. Register the plug-in for discovery

Add an import to `src/exphub/beamlines/__init__.py`:

```python
from . import gpsans  # noqa: F401
```

Order matters only for the *default* active beamline (the first registered wins
until a launcher / selector overrides at runtime).

## 5. Write the prompt fragment

`prompts/context.md` is a 30-80 line Markdown block introducing GP-SANS
(Q range, sample-aperture / detector-distance configurations, file-path
conventions). The composer inserts it after the SANS *technique* context and
before the active task. Reference `beamlines/usans/prompts/context.md`.

## 6. (Optional) Override a tab

If GP-SANS needs a real Instrument Status tab (most beamlines do — detector
layout and PV names vary), add `tabs/css_status.py` defining a class that takes
the steering view-model, then wire it through `BeamlineSpec.tabs`:

```python
from ...core.beamline import TabOverrides

def _build_css_status(view_model):
    from .tabs.css_status import CSSStatusView
    return CSSStatusView(view_model)

GPSANS = BeamlineSpec(..., tabs=TabOverrides(css_status=_build_css_status))
```

The **lazy-import closure** is required — eager view imports at spec-construction
time create circular dependencies. The dispatcher resolves overrides via
`manifest.tab_override_slots`, so the `TabOverrides` field names
(`experiment_info`, `temporal_analysis`, `angle_plan`, `css_status`,
`data_analysis`) are generic slot 1-5 names shared by every technique — use them
verbatim regardless of technique.

## 7. (Optional) Knowledge base

Drop Markdown under `knowledge/`. The RAG indexer picks it up automatically and
ChromaDB persistence is keyed per beamline so switches do not rebuild the index.

## 8. Verify

```
.pixi/envs/default/bin/python -m pytest -q
```

- `tests/test_beamline_coupling.py` — asserts no per-beamline strings leak
  outside `beamlines/<id>/` (stays at zero).
- `tests/test_multi_technique.py` / `tests/test_multi_beamline.py` — registration,
  runtime switching, and per-`(beamline, technique)` `MainApp()` construction.

Smoke check from a REPL:

```python
import exphub.beamlines  # registers all
from exphub.core.beamline import list_ids, set_active, active_technique, BeamlineContext
print(list_ids())
spec = set_active("gpsans")
print(spec.technique, active_technique().display_name)   # sans, Small-Angle ...
ctx = BeamlineContext(spec)
print(ctx.ipts_root(12345))
```

## 9. Notes and caveats

- **Cross-technique switching is restart-gated (v1).** Selecting GP-SANS from a
  single-crystal session (or vice versa) requires a restart; the selector grays
  the cross-technique option with a banner. True hot-rebuild is deferred
  (`MULTI_TECHNIQUE_PLAN.md` -> P3a-future).
- **Provisional values.** PVs / URLs you do not yet have go to `None`/`""` and
  are documented inline, exactly as USANS does. Do not invent PVs.
- **EIC server.** SANS beamlines point at a different EIC server from the
  single-crystal beamlines via `EICSpec.server_url`; an empty string lets the
  vendored client derive the URL from `beamline_code`.
- **A new technique** (not just a beamline) is a different job — see
  [adding_a_technique.md](adding_a_technique.md).
