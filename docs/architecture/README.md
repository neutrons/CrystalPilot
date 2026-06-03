# ExpHub architecture overview

ExpHub (the `exphub` package, historically "CrystalPilot") is layered so that a
new *technique family* or a new *beamline* is added by dropping in files, never
by editing the framework. Five layers, each documented on its own page:

| Layer | Page | Owns |
|---|---|---|
| core | [core.md](core.md) | Beamline + technique registries, specs, paths, EIC pipeline |
| techniques | [techniques.md](techniques.md) | Experiment *shape*: tabs, models, agent phases/verbs, prompts |
| beamlines | [beamlines.md](beamlines.md) | Per-instrument parameters (PVs, paths) + tab overrides |
| app | [app.md](app.md) | Trame shell, MVVM wiring, manifest-driven tab dispatcher |
| agent | [agent.md](agent.md) | LLM chat, schema/tools, phase machine, prompt composer, RAG |

Working two techniques at once? See
[`../parallel_development.md`](../parallel_development.md) — the lanes, the
CI-enforced boundaries, and the branching model that keep TOPAZ and USANS
development from colliding.

## How the layers stack

```
                 +-------------------------------------+
   user <------> |  app  (trame shell, MVVM, dispatch) |
                 +------------------+------------------+
                                    | reads active manifest + spec
              +---------------------+---------------------+
              |                                           |
     +--------v---------+                       +---------v--------+
     |   techniques     |  one technique per    |    beamlines     |
     | (single_crystal, |<----------------------|  (topaz, corelli,|
     |  sans)           |   beamline.technique  |   usans)         |
     +--------+---------+                       +---------+--------+
              |                                           |
              +---------------------+---------------------+
                                    | both register into
                          +---------v---------+
                          |       core        |
                          | registries, spec, |
                          | paths, eic, tabs  |
                          +-------------------+
                                    ^
                          +---------+---------+
                          |       agent       |
                          | reads manifest +  |
                          | spec for schema,  |
                          | phases, prompts   |
                          +-------------------+
```

## The two plug-in points

- A **technique manifest**
  (`core.beamline.technique.TechniqueManifest`) declares *what an experiment of
  this kind looks like*: the five tab slots, the agent's phase sequence and
  action verbs, the prompt/RAG corpus, the root data model, and the EIC row
  builder. Lives in `techniques/<id>/`.
- A **beamline spec** (`core.beamline.spec.BeamlineSpec`) selects exactly one
  technique and supplies *per-instrument* values (PVs, file-system roots, EIC
  server) plus optional per-tab overrides. Lives in `beamlines/<id>/`.

The app shell and agent read both objects at runtime through the registries and
never name a technique or beamline class directly. See
[adding_a_technique.md](../adding_a_technique.md) and
[adding_a_beamline.md](../adding_a_beamline.md) for the onboarding walk-throughs.
