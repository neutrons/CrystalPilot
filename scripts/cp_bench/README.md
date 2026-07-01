# CP-Bench

Standalone, headless benchmark that replays historical TOPAZ runs as
time-sliced "fake live data", applies CrystalPilot's live early-stopping rule
to pick a cutoff time, reduces the pre-cutoff window with the beamline's own
reduction config, and compares it against the full-run reduction.

Full design + rationale: [`../../CP_BENCH_PLAN.md`](../../CP_BENCH_PLAN.md).

## Safety: `/SNS` is read-only

Every write goes through [`safety.py`](safety.py), which resolves the real path
(following symlinks) and **refuses any write on or under `/SNS`** (extend the
protected roots with `CP_BENCH_READONLY_ROOTS`). `/SNS` is only ever *read*
(NeXus files, reduction configs). All output lands under
`<out>/IPTS-<n>/CP-bench/<run>/<timestamp>/` (default `<out>` = `~`).

## Usage

```bash
# discovery only — lists runs + configs, writes nothing:
python -m scripts.cp_bench --ipts 35036 --dry-run

# full benchmark (needs the ReduceSCD driver on the analysis node):
python -m scripts.cp_bench --ipts 35036 --runs 12,15,20:23 \
    --reducer /SNS/TOPAZ/shared/.../ReduceSCD_Parallel.py \
    --cutoff-strategy by_uncertainty --cutoff-threshold 0.1 \
    --grid log --n-steps 12 --out ~
```

## Architecture

Pure logic (discovery parsing, cutoff rules, comparison, recording) is separated
from side effects (Mantid + the reducer subprocess), which live behind injected
adapters in [`adapters/`](adapters/). The pure/orchestration modules are unit
tested with fakes (`tests/cp_bench/`) and need neither Mantid nor `/SNS`.

| Module | Phase |
|---|---|
| `discover.py` | find NeXus files + reduction configs, extract run info |
| `metrics.py` | quality metrics vs elapsed time (reuses the app pipeline) |
| `cutoff.py` | pick the early-stop time from the metrics |
| `reduce.py` | run ReduceSCD on the full window and the pre-cutoff window |
| `compare.py` | partial-vs-full deltas + efficiency headline |
| `record.py` / `batch.py` | output layout, provenance, orchestration |

## To confirm on the analysis server (see CP_BENCH_PLAN §9)

- The `shared/ReductionGUI/` config dialect and whether the stock reducer's
  loader accepts the pre-sliced partial NeXus (`adapters/reducescd.py`
  `save_algorithm` / `filename_pattern` are parameters for this reason).
- Monitor-workspace survival through `FilterByTimeStop`.
- The point group to feed merge statistics (`--point-group`).
