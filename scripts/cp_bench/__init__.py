"""CP-Bench — early-stopping reduction benchmark for TOPAZ (standalone harness).

This package is a *tool*, not app surface. It reuses the CrystalPilot
single-crystal live-reduction pipeline as a library (headless, no trame/GUI)
to answer: if the live-monitoring early-stopping rule had been applied to a
historical run, how much crystallographic quality would have been lost versus
running to completion, for how much saved beam time?

Design invariants (see ``CP_BENCH_PLAN.md``):

* ``/SNS`` is **read-only** — every write goes through :mod:`.safety`, which
  refuses any path that resolves under a protected root.
* Pure logic (discovery parsing, cutoff rules, comparison) is separated from
  Mantid/reducer side effects (isolated behind injectable adapters in
  :mod:`.adapters`) so the harness is unit-testable without Mantid or /SNS.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
