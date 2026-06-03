# Layer: beamlines (`exphub.beamlines`)

A *beamline* is one physical instrument. It plugs into exactly one technique
family and supplies only **per-instrument** parameters — EPICS PVs, file-system
roots, the EIC server, agent context — plus optional per-tab overrides. It
never re-declares tab shapes, models, phases, or verbs; those come from the
technique manifest.

## What lives here

```
beamlines/<id>/
├── __init__.py          imports .spec so register() fires on import
├── spec.py              the BeamlineSpec instance + register(SPEC) call
├── gonio.py             goniometer PV tables (single-crystal only; omit otherwise)
├── prompts/context.md   per-beamline agent prompt fragment
├── knowledge/*.md       per-beamline RAG documents
├── screens/             optional Phoebus .bob assets for the Status tab
└── tabs/                optional per-beamline tab content overrides
```

Shipped: `topaz`, `corelli` (single-crystal) and `usans` (sans).

## What the spec declares

`technique_config` (a `SingleCrystalConfig` or `SansConfig` — the discriminator
also sets `technique`), `detector`/`paths`/`eic`/`agent` sub-specs,
`tabs` (a `TabOverrides` of lazy tab factories), and `placeholder_messages`/
`placeholder_links` for slots with no real tab yet.

```
   BeamlineSpec.technique_config.kind  --->  selects the technique manifest
   BeamlineSpec.tabs.<slot>            --->  overrides one tab (else default)
   BeamlineSpec.eic / paths / detector --->  PVs + roots for this instrument
```

## Discovery

`beamlines/__init__.py` imports every plug-in package; the first registered is
the default active beamline. The registry also lazy-imports `beamlines.<id>` on
demand.

## Rule of thumb

If it is the *same kind of experiment* on a *different machine*, it is a new
beamline, not a new technique. See [adding_a_beamline.md](../adding_a_beamline.md).
