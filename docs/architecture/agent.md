# Layer: agent (`exphub.agent`)

The LLM assistant. It reads the live Pydantic model the tabs use, exposes a
typed tool surface to the model, runs a per-technique phase machine, and
composes a layered system prompt. Like the app shell it is **parametrised** by
the active technique manifest and beamline spec — it hard-codes no
single-crystal knowledge.

## What lives here

```
agent/
├── agent.py            top-level orchestration
├── mcp_service.py      MCP tool server wiring
├── tools.py            set_parameter / append_run / navigate_to_tab / action verbs
├── schema_gen.py       Pydantic models -> JSON schema for set_parameter
├── bridge.py           bridged_submodels()/field_owner() from the manifest
├── workflow.py         PhaseManager state machine (sequence from manifest)
├── prompts/composer.py 4-layer system-prompt assembler
├── rag.py              ChromaDB retrieval over the per-technique knowledge dir
└── constants.py, state.py, handlers.py, llm.py, utils.py
```

## How a technique parametrises it

```
manifest.phases          --->  workflow.PhaseManager sequence
manifest.action_tools    --->  tools.make_tools() extra verbs (resolve vm_method)
manifest.bridged_submodels --> bridge / schema_gen field surface
manifest.prompts_dir     --->  composer technique-context layer
manifest.knowledge_dir   --->  rag corpus
```

Prompt layers, in order: **core identity** -> **technique context**
(`techniques/<id>/prompts/context.md`) -> **beamline context**
(`beamlines/<id>/prompts/context.md`) -> **active task**.

## Rule of thumb

After a restart-switch to another technique, `set_parameter` exposes only that
technique's fields, the PhaseManager runs that technique's phases, and the
prompt swaps its technique + beamline layers. No agent code edit is needed for a
new technique. See [architecture/techniques.md](techniques.md).
