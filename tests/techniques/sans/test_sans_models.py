"""SANS technique model tests (the SANS lane's home).

Mirrors ``tests/techniques/single_crystal/`` for the SANS technique. These
exercise only ``techniques/sans/`` and are owned by the SANS lane; the SANS
developer can churn them freely without touching single-crystal tests.
"""

from __future__ import annotations

from exphub.techniques.sans.models.root import SansMainModel


def test_sans_root_model_constructs_with_sans_submodels() -> None:
    model = SansMainModel()
    # SANS-shaped sub-models (no goniometer / angle plan / UB).
    assert hasattr(model, "iptsinfo")
    assert hasattr(model, "strategy")
    assert hasattr(model, "iqreduction")


def test_sans_ipts_has_no_single_crystal_fields() -> None:
    """The SANS tab-1 model is genuinely a different shape, not single-crystal."""
    ipts = SansMainModel().iptsinfo
    for sc_field in ("crystalsystem", "point_group", "centering", "UBFileName"):
        assert not hasattr(ipts, sc_field), f"SANS ipts model unexpectedly carries single-crystal field {sc_field!r}"


def test_sans_root_has_no_single_crystal_submodels() -> None:
    model = SansMainModel()
    for sc_submodel in ("angleplan", "experimentinfo", "temporalanalysis", "cssstatus"):
        assert not hasattr(model, sc_submodel), (
            f"SANS root model unexpectedly carries single-crystal sub-model {sc_submodel!r}"
        )
