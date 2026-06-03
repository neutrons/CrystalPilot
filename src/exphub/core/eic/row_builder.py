"""EIC row-builder seam (P3a.2).

The framework-agnostic EIC pipeline (:mod:`exphub.core.eic.control`) submits
*pre-built* table-scan jobs and never inspects column names. The per-technique
CSV column layout (which PV columns exist, how a strategy row maps onto them)
lives behind this seam: each technique declares an ``EICRowBuilder`` on its
:class:`~exphub.core.beamline.technique.TechniqueManifest`, and the submit path
resolves ``active_technique().eic_row_builder`` to turn its editable
strategy-table rows into EIC submission payloads.

A builder produces *jobs*: one payload per strategy row. Each job carries the
EIC table-scan ``headers`` + ``row`` to submit plus the display metadata the
EIC Control panel renders (``title`` and, for goniometer techniques, ``phi`` /
``omega``). Headers travel per-row because a single strategy may mix row shapes
(e.g. an angle row vs a temperature-ramp row in single crystal).

``build_rows`` is the flat convenience form named in the plan
(``build_rows(strategy_rows, ipts, spec) -> (headers, rows)``); it is only
well-defined when every job in a plan shares one header layout, so it asserts
that and is intended for tests / homogeneous techniques rather than the live
single-crystal submit path (which uses :meth:`build_jobs` directly).
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol, Tuple, runtime_checkable


@runtime_checkable
class EICRowBuilder(Protocol):
    """Per-technique translator from strategy-table rows to EIC payloads."""

    def build_jobs(
        self,
        strategy_rows: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Build one EIC submission payload per strategy row.

        Each returned dict carries the EIC table-scan ``headers`` and ``row``
        to submit plus display metadata (``title``; ``phi`` / ``omega`` for
        goniometer techniques).
        """
        ...

    def build_rows(
        self,
        strategy_rows: List[Dict[str, Any]],
        ipts: str = "",
        spec: Any = None,
        **kwargs: Any,
    ) -> Tuple[List[str], List[List[Any]]]:
        """Return ``(headers, rows)`` for a homogeneous strategy plan."""
        ...


__all__ = ["EICRowBuilder"]
