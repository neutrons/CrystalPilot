# Adding a new technique family

A *technique family* owns the **shape** of an experiment: which tabs exist and
how they look, the data model behind them, the agent's phase machine and action
verbs, and the prompt/RAG corpus. Beamlines plug into a technique and supply
only per-instrument values. ExpHub ships two techniques today —
`single_crystal` and `sans` — and is designed so a third one drops into
`src/exphub/techniques/<id>/` with **no edits to `core/`, `app/`, or `agent/`**.

This guide adds a worked **reflectometry** technique end to end. Use the shipped
`sans` package (`src/exphub/techniques/sans/`) as the canonical template — it is
the most recent technique and was built specifically to prove this seam.

See `MULTI_TECHNIQUE_PLAN.md` (repo root) for the full design rationale, and
[architecture/techniques.md](architecture/techniques.md) for the one-page map.

---

## When is it a new technique vs. a new beamline?

Decide before you start (see also the decision tree in
[adding_a_beamline.md](adding_a_beamline.md)):

- **Same kind of experiment on a different machine** -> new *beamline* of an
  existing technique. GP-SANS at HFIR is the same technique as USANS; it is a
  new beamline, not a new technique.
- **A genuinely different experiment** — different tabs, different data model,
  different agent workflow, different physics vocabulary -> new *technique*.
  Reflectometry (specular R(Q) off a flat surface) has its own reduction,
  geometry, and steering, so it is a new technique.

If you only need to change PVs, paths, the EIC server, or swap one tab's view,
stop here and read [adding_a_beamline.md](adding_a_beamline.md) instead.

---

## 1. Pick an id and scaffold the package

Lowercase, no spaces, matches the directory name. We use `reflectometry`.

```
src/exphub/techniques/reflectometry/
├── __init__.py            imports .manifest so register_technique() fires
├── manifest.py            the TechniqueManifest instance (the plug-in point)
├── models/
│   ├── __init__.py
│   ├── root.py            ReflMainModel composite root
│   ├── sample_info.py     IPTS / sample sub-model
│   ├── strategy.py        angle/Q scan strategy table sub-model
│   └── rq_reduction.py    R(Q) reduction sub-model (placeholder ok)
├── view_models/
│   ├── __init__.py
│   └── steering.py        ReflSteeringViewModel (owns the *_bind attributes)
├── views/
│   ├── __init__.py
│   ├── sample_info.py     tab 1 content
│   ├── rq_reduction.py    tab 2 content (live)
│   └── strategy.py        tab 3 content (steering + EIC control)
├── agent/
│   ├── __init__.py
│   ├── phases.py          REFLECTOMETRY_PHASES
│   └── eic_row_builder.py REFLECTOMETRY_EIC_ROW_BUILDER
└── prompts/
    └── context.md         technique prompt fragment
```

The minimum viable technique is `__init__.py` + `manifest.py` +
`models/root.py` + a steering VM + the three default tab views + `prompts/`.

`__init__.py` only needs to import the manifest so registration fires:

```python
"""Reflectometry technique family."""
from .manifest import REFLECTOMETRY  # noqa: F401 — registers on import
```

## 2. Build the root model and sub-models (`models/`)

The root is a small Pydantic composite of one sub-model per tab plus the shared
EIC control model. Mirror `techniques/sans/models/root.py`:

```python
from pydantic import BaseModel, Field
from ....core.eic import EICControlModel
from .sample_info import ReflSampleInfoModel
from .strategy import ReflStrategyModel
from .rq_reduction import ReflRQReductionModel

class ReflMainModel(BaseModel):
    sampleinfo: ReflSampleInfoModel = Field(default_factory=ReflSampleInfoModel)
    strategy:   ReflStrategyModel   = Field(default_factory=ReflStrategyModel)
    rqreduction: ReflRQReductionModel = Field(default_factory=ReflRQReductionModel)
    eiccontrol: EICControlModel = Field(default_factory=EICControlModel)
```

The sub-model field names (`sampleinfo`, `strategy`, ...) are the
`bridged_submodels` the agent reads/writes and the names the steering VM binds —
keep them consistent across model, manifest, and VM.

## 3. Build the steering view-model (`view_models/steering.py`)

The orchestration VM owns the technique's tab state. It must:

- take `(root_model, binding, notify_fn=None)` in its constructor (the signature
  `mvvm_factory` calls),
- expose one `<name>_bind` attribute per `bridged_submodels` entry (e.g.
  `sampleinfo_bind`, `strategy_bind`, `rqreduction_bind`, `eiccontrol_bind`),
- expose the `vm_method`s named by the manifest's `action_tools` (e.g.
  `submit_strategy`, `call_load_token`, `stoprun`),
- provide `on_deactivate()` (cancel async tasks / clear buffers — called by the
  shell on an inside-technique beamline switch).

Copy `techniques/sans/view_models/steering.py` and reduce/rename to the
reflectometry shape. SANS has no goniometer angle plan and no Mantid live loop;
reflectometry will have an incidence-angle / Q-scan plan, so model that table in
`strategy.py`.

## 4. Build the default tab views (`views/`)

One trame view module per default tab. Each is a class taking the steering VM:

```python
class ReflSampleInfoView:
    def __init__(self, view_model): ...
```

Bind widgets to the steering VM's `<name>_bind` surface, exactly as the SANS
views do. Keep the views technique-pure — no `app/` shell imports.

## 5. Declare the agent contract (`agent/`)

- **`phases.py`** — a `tuple[PhaseDefinition, ...]` mapping your workflow onto
  the five `TabKey` slots. Reflectometry phases, e.g.: `setup` (IPTS/sample) ->
  `configure_q_range` (R(Q) binning) -> `load_strategy` (angle scan plan) ->
  `monitor_reduction` -> `save`. Mirror `techniques/sans/agent/phases.py`.
- **`eic_row_builder.py`** — an object implementing the `EICRowBuilder` Protocol
  (`core/eic/row_builder.py`): `write_strategy_csv`, `build_jobs`, `build_rows`.
  It turns your strategy rows into EIC table-scan payloads. If the column layout
  is not yet specified, ship a provisional builder and document it (as SANS did).

## 6. Write the prompt fragment (`prompts/context.md`)

A short Markdown block introducing reflectometry to the agent (specular vs.
off-specular, Q range from incidence angle, footprint/over-illumination
caveats). The composer inserts it between the core identity and the beamline
context. Optionally add per-task files under `prompts/tasks/`.

## 7. Assemble the manifest (`manifest.py`)

This is the single plug-in point. Copy `techniques/sans/manifest.py` and fill in
your factories. The shape:

```python
from ...core.beamline.technique import (
    ActionTool, TabKey, TechniqueManifest, register_technique,
)
from .agent.eic_row_builder import REFLECTOMETRY_EIC_ROW_BUILDER
from .agent.phases import REFLECTOMETRY_PHASES
from .models.root import ReflMainModel

def _sample_tab(vm):  from .views.sample_info import ReflSampleInfoView; return ReflSampleInfoView(vm)
def _live_tab(vm):    from .views.rq_reduction import ReflRQReductionView; return ReflRQReductionView(vm)
def _steer_tab(vm):   from .views.strategy import ReflStrategyView; return ReflStrategyView(vm)

def _build_steering_vm(model, binding, notify_fn=None):
    from .view_models.steering import ReflSteeringViewModel
    return ReflSteeringViewModel(model, binding, notify_fn=notify_fn)

REFLECTOMETRY = register_technique(TechniqueManifest(
    id="reflectometry",
    display_name="Neutron Reflectometry",
    default_tabs={TabKey.IPTS: _sample_tab, TabKey.LIVE: _live_tab, TabKey.STEERING: _steer_tab},
    tab_override_slots={
        TabKey.IPTS: "experiment_info", TabKey.LIVE: "temporal_analysis",
        TabKey.STEERING: "angle_plan",  TabKey.STATUS: "css_status",
        TabKey.ANALYSIS: "data_analysis",
    },
    tab_labels={
        TabKey.IPTS: "Sample Info", TabKey.LIVE: "R(Q) Reduction",
        TabKey.STEERING: "Experiment Steering", TabKey.STATUS: "Instrument Status",
        TabKey.ANALYSIS: "Data Analysis",
    },
    tab_aliases={"sample": TabKey.IPTS, "rq": TabKey.LIVE, "reflectivity": TabKey.LIVE,
                 "strategy": TabKey.STEERING},
    bridged_submodels=("sampleinfo", "strategy", "rqreduction", "eiccontrol"),
    field_owner={"instrument": "sampleinfo"},
    phases=REFLECTOMETRY_PHASES,
    action_tools=(ActionTool(name="submit_strategy", vm_method="submit_strategy",
                             description="Submit the reflectometry scan strategy to EIC.",
                             success_message="Strategy submitted to EIC."), ...),
    prompts_dir=Path(__file__).resolve().parent / "prompts",
    eic_row_builder=REFLECTOMETRY_EIC_ROW_BUILDER,
    root_model_factory=ReflMainModel,
    steering_vm_factory=_build_steering_vm,
))
```

Notes on the `tab_override_slots`: those `TabOverrides` field names
(`experiment_info`, `temporal_analysis`, `angle_plan`, ...) are
single-crystal-shaped today and shared by every technique as generic slot 1-5
names; reuse them verbatim. `STATUS` and `ANALYSIS` get no `default_tabs` entry,
so beamlines supply them via a tab override or fall through to a placeholder.

## 8. Add the technique config to the spec union (one framework touch)

`BeamlineSpec.technique_config` is a discriminated union. To let a beamline
declare `technique="reflectometry"`, add a `ReflectometryConfig(kind=...)` to
`core/beamline/spec.py` and extend the union + the `technique` `Literal`. This
is the **only** edit outside `techniques/reflectometry/`, and it is a clean
typed addition, not a new `Optional` field. (A reflectometry beamline then ships
under `beamlines/<id>/` — see [adding_a_beamline.md](adding_a_beamline.md).)

## 9. Verify

```
.pixi/envs/default/bin/python -m pytest -q
```

- `tests/test_technique_coupling.py` — the ratchet asserting single-crystal
  vocabulary stays inside `techniques/single_crystal/`. Adding a clean technique
  must not raise any BASELINE count.
- `tests/test_multi_technique.py` — registration, manifest contract, and
  per-`(beamline, technique)` `MainApp()` construction.

Smoke check from a REPL:

```python
import exphub.techniques.reflectometry  # registers
from exphub.core.beamline import get_technique
m = get_technique("reflectometry")
print(m.display_name, list(m.default_tabs), [t.name for t in m.action_tools])
print(m.root_model_factory())          # constructs the composite root
```

## 10. Checklist

- [ ] `__init__.py` imports `.manifest`
- [ ] root model composes one sub-model per `bridged_submodels` entry + `eiccontrol`
- [ ] steering VM constructor is `(model, binding, notify_fn=None)`, exposes all
      `<name>_bind` + every `action_tools` `vm_method` + `on_deactivate()`
- [ ] one view per `default_tabs` entry
- [ ] `phases.py` and `eic_row_builder.py` present
- [ ] `prompts/context.md` present
- [ ] manifest registered; `STATUS`/`ANALYSIS` left to beamline/placeholder
- [ ] new `ReflectometryConfig` added to the spec union (the only framework edit)
- [ ] full suite green; ratchet not raised
