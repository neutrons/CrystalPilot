# Layer: techniques (`exphub.techniques`)

A *technique family* (single-crystal diffraction, SANS, ...) owns the **shape**
of an experiment: which tabs exist and how they look, the data model behind
them, the agent's phase machine and action verbs, and the prompt/RAG corpus. A
beamline plugs into exactly one technique and never re-declares any of this.

## What lives here

```
techniques/<id>/
├── __init__.py          imports .manifest so register_technique() fires
├── manifest.py          the TechniqueManifest instance (single plug-in point)
├── models/              root.py composite + per-tab Pydantic sub-models
├── view_models/         steering.py orchestration VM (the *_bind attributes)
├── views/               trame tab content (one module per default tab)
├── agent/               phases.py, eic_row_builder.py (+ validation, single_crystal)
└── prompts/             context.md technique fragment (+ tasks/ optional)
```

Shipped: `single_crystal` (TOPAZ, CORELLI) and `sans` (USANS).

## What the manifest declares

`default_tabs` (tab factories), `tab_labels`/`tab_aliases`,
`bridged_submodels` + `field_owner` (which model fields the agent reads/writes),
`phases` (PhaseManager sequence), `action_tools` (LLM verbs), `prompts_dir`,
`root_model_factory`, `steering_vm_factory`, and `eic_row_builder`.

```
   manifest.default_tabs[TabKey]  --->  app dispatcher renders tab
   manifest.phases                --->  agent PhaseManager
   manifest.action_tools          --->  agent tool surface
   manifest.root_model_factory()  --->  the composite Pydantic root
   manifest.steering_vm_factory   --->  the VM whose *_bind back the tabs
```

## Rule of thumb

Anything that varies by *kind of experiment* (not by instrument) lives here.
Per-instrument PVs and paths go to the beamline layer. See
[adding_a_technique.md](../adding_a_technique.md).
