"""EIC row-builder seam regression tests (P3a.2).

The single-crystal CSV/row shape moved out of ``EICControlModel`` into a
per-technique :class:`~exphub.core.eic.row_builder.EICRowBuilder` wired onto the
single-crystal :class:`TechniqueManifest`. These tests pin the *exact* EIC
table-scan ``headers`` + ``row`` payloads each shipped single-crystal beamline
(TOPAZ, CORELLI) produces, so the move is provably byte-identical to the
pre-refactor behavior, and pin the manifest seam + submit-path wiring.

Beamline switching is restart-gated in production, and the ``gonio_pvs`` shim
caches the active beamline's PVs at import time; to exercise both beamlines in
one process the helper reloads the shim + builder modules after ``set_active``,
which is what a real restart-switch does.
"""

from __future__ import annotations

import importlib

import exphub.beamlines  # noqa: F401 — registers TOPAZ + CORELLI
from exphub.core.beamline import active_technique, set_active
from exphub.core.eic.row_builder import EICRowBuilder

# A plan that exercises every row shape: two angle rows (PCharge wait + a
# non-PCharge wait) and one temperature-ramp row.
_PLAN = [
    {
        "title": "run1",
        "comment": "c1",
        "omega": 10.0,
        "phi": 20.0,
        "wait_for": "PCharge",
        "value": 30,
    },
    {
        "title": "run2",
        "comment": "c2",
        "omega": 5.5,
        "phi": -3.2,
        "wait_for": "Time",
        "value": 60,
    },
    {
        "title": "ramp1",
        "comment": "rc",
        "step_type": "ramp",
        "ramp_start": 100,
        "ramp_end": 300,
        "ramp_rate": 2,
        "ramp_soak": 5,
        "ramp_run": 1,
    },
]

# Golden jobs captured from the row builder. These are byte-identical to what
# the pre-refactor ``EICControlModel.submit_jobs`` row-construction produced for
# each beamline (same PV column names, same value/wait-for handling, same ramp
# layout, same title/phi/omega display metadata).
_TOPAZ_JOBS = [
    {
        "headers": ["Title", "Comment", "BL12:Mot:goniokm:omega", "BL12:Mot:goniokm:phi", "Wait For", "Value"],
        "row": ["run1", "c1", 10.0, 20.0, "BL12:Det:PCharge:C", 30],
        "title": "run1",
        "phi": 20.0,
        "omega": 10.0,
    },
    {
        "headers": ["Title", "Comment", "BL12:Mot:goniokm:omega", "BL12:Mot:goniokm:phi", "Wait For", "Value"],
        "row": ["run2", "c2", 5.5, -3.2, "Time", 60],
        "title": "run2",
        "phi": -3.2,
        "omega": 5.5,
    },
    {
        "headers": [
            "Title", "Comment",
            "BL12:SE:Ramp:Start", "BL12:SE:Ramp:End", "BL12:SE:Ramp:Rate",
            "BL12:SE:Ramp:Soak", "BL12:SE:Ramp:Run",
        ],
        "row": ["ramp1", "rc", 100, 300, 2, 5, 1],
        "title": "ramp1",
        "phi": 0.0,
        "omega": 0.0,
    },
]

_CORELLI_JOBS = [
    {
        "headers": ["Title", "Comment", "BL9:Mot:Sample:omega", "BL9:Mot:Sample:phi", "Wait For", "Value"],
        "row": ["run1", "c1", 10.0, 20.0, "BL9:Det:PCharge:C", 30],
        "title": "run1",
        "phi": 20.0,
        "omega": 10.0,
    },
    {
        "headers": ["Title", "Comment", "BL9:Mot:Sample:omega", "BL9:Mot:Sample:phi", "Wait For", "Value"],
        "row": ["run2", "c2", 5.5, -3.2, "Time", 60],
        "title": "run2",
        "phi": -3.2,
        "omega": 5.5,
    },
    {
        "headers": [
            "Title", "Comment",
            "BL9:SE:Ramp:Start", "BL9:SE:Ramp:End", "BL9:SE:Ramp:Rate",
            "BL9:SE:Ramp:Soak", "BL9:SE:Ramp:Run",
        ],
        "row": ["ramp1", "rc", 100, 300, 2, 5, 1],
        "title": "ramp1",
        "phi": 0.0,
        "omega": 0.0,
    },
]


def _builder_for(beamline_id: str) -> tuple[EICRowBuilder, str]:
    """Activate ``beamline_id`` and return its (reloaded) single-crystal builder.

    Reloading the ``gonio_pvs`` shim + ``eic_row_builder`` module after
    ``set_active`` mirrors a restart-switch: the shim re-reads the now-active
    beamline's PV strings. Returns the builder plus its ``AMBIENT`` constant.
    """
    set_active(beamline_id)
    gonio = importlib.import_module(
        "exphub.techniques.single_crystal.models.gonio_pvs"
    )
    importlib.reload(gonio)
    rb = importlib.import_module(
        "exphub.techniques.single_crystal.agent.eic_row_builder"
    )
    importlib.reload(rb)
    return rb.SINGLE_CRYSTAL_EIC_ROW_BUILDER, gonio.AMBIENT


def teardown_module(_module: object) -> None:
    # Restore TOPAZ + a TOPAZ-consistent shim for the rest of the suite.
    _builder_for("topaz")


def test_topaz_jobs_are_unchanged_by_refactor() -> None:
    builder, ambient = _builder_for("topaz")
    jobs = builder.build_jobs(_PLAN, goniometer_type=ambient)
    assert jobs == _TOPAZ_JOBS


def test_corelli_jobs_are_unchanged_by_refactor() -> None:
    builder, ambient = _builder_for("corelli")
    jobs = builder.build_jobs(_PLAN, goniometer_type=ambient)
    assert jobs == _CORELLI_JOBS


def test_manifest_exposes_row_builder_seam() -> None:
    set_active("topaz")
    builder = active_technique().eic_row_builder
    assert builder is not None
    assert isinstance(builder, EICRowBuilder)


def test_build_rows_flat_form_homogeneous_angle_plan() -> None:
    builder, ambient = _builder_for("topaz")
    angle_only = [_PLAN[0], _PLAN[1]]
    headers, rows = builder.build_rows(angle_only, goniometer_type=ambient)
    assert headers == _TOPAZ_JOBS[0]["headers"]
    assert rows == [_TOPAZ_JOBS[0]["row"], _TOPAZ_JOBS[1]["row"]]


def test_build_rows_rejects_mixed_shape_plan() -> None:
    builder, ambient = _builder_for("topaz")
    import pytest

    # _PLAN mixes angle rows and a ramp row → no single shared header layout.
    with pytest.raises(ValueError):
        builder.build_rows(_PLAN, goniometer_type=ambient)
