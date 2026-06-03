# Layer: core (`exphub.core`)

The technique-agnostic framework. Knows nothing about crystallography, SANS, or
any specific instrument; it provides the registries, contracts, and shared
services every technique and beamline plugs into.

## What lives here

```
core/
├── beamline/
│   ├── spec.py        BeamlineSpec + technique-config discriminated union
│   ├── registry.py    register() / active() / set_active() / list_ids()
│   ├── context.py     BeamlineContext: PV + path helpers for the active spec
│   └── technique.py    TechniqueManifest, TabKey, register_technique()/...
├── paths/resolver.py  IPTS-aware path composition (autoreduce, dropbox, ...)
├── eic/
│   ├── control.py     framework-agnostic EIC table-scan submit pipeline
│   ├── eic_client.py  vendored EIC HTTP client
│   └── row_builder.py EICRowBuilder Protocol (per-technique CSV column seam)
└── tabs/, pvs/, tasks/  shared small helpers
```

## Contracts it owns

- **`BeamlineSpec`** — discriminated on `technique_config.kind`, so a new
  technique gets a clean config class instead of a wall of `Optional` fields.
- **`TechniqueManifest`** — the per-technique plug-in record (tabs, phases,
  action verbs, models, prompts, EIC row builder).
- **Two registries** — both lazy-import `exphub.{beamlines,techniques}.<id>`
  on first lookup; importing the package triggers its `register*` side effect.
- **`EICRowBuilder`** Protocol — keeps the EIC submit path from ever inspecting
  technique-specific CSV columns.

## Rule of thumb

If code would need editing to add a technique or beamline, it does **not**
belong in `core`. The acceptance ratchet (`tests/test_technique_coupling.py`)
guards against single-crystal vocabulary leaking back in.
