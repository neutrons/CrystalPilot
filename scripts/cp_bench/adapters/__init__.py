"""Side-effecting adapters: the only place CP-Bench touches Mantid or subprocess.

Each adapter implements a ``Protocol`` from the pure modules
(``MetadataReader``, ``ReductionEngine``, ``Reducer``) and is injected at the
CLI boundary. Mantid and the CrystalPilot pipeline are imported lazily *inside*
methods so the pure/orchestration modules stay importable (and testable)
without Mantid installed. Every write path is routed through
:mod:`cp_bench.safety`, so no adapter can modify ``/SNS``.
"""
