"""Tests for the discriminated ``technique_config`` spec payload (P0.5).

See ``MULTI_TECHNIQUE_PLAN.md`` — the spec evolved from a flat bag of
single-crystal fields to a discriminated union keyed on ``kind``. These tests
pin the three behaviours the rest of the refactor relies on:

- the ``technique`` field stays in step with ``technique_config.kind``
- ``BeamlineSpec.single_crystal`` narrows the union (and raises for non-SC)
- the shipped TOPAZ / CORELLI specs carry their values under the new payload
"""

from __future__ import annotations

from typing import cast

import pytest

import exphub.beamlines  # noqa: F401 — triggers registration
from exphub.core.beamline import (
    BeamlineContext,
    BeamlineSpec,
    SansConfig,
    SingleCrystalConfig,
    get,
    set_active,
)

# ---------- shipped beamlines migrated to the discriminated payload ----------


def test_topaz_carries_single_crystal_config() -> None:
    spec = get("topaz")
    assert spec.technique == "single_crystal"
    assert isinstance(spec.technique_config, SingleCrystalConfig)
    sc = spec.single_crystal
    assert sc.mantid.instrument_name == "TOPAZ"
    assert sc.goniometer.angle_pvs["omega"] == "BL12:Mot:goniokm:omega"
    assert sc.run_title_pv == "BL12:SMS:RunInfo:RunTitle"
    assert sc.default_calibration.endswith("calibration.DetCal")
    assert str(sc.bob_screen_path).endswith("BL12_ADnED_2D_4x4.bob")


def test_corelli_carries_single_crystal_config() -> None:
    spec = get("corelli")
    assert spec.technique == "single_crystal"
    assert isinstance(spec.technique_config, SingleCrystalConfig)
    assert spec.single_crystal.mantid.instrument_name == "CORELLI"
    # No .bob shipped for CORELLI yet.
    assert spec.single_crystal.bob_screen_path is None


def test_context_reads_through_discriminator() -> None:
    """The runtime accessor resolves goniometer + screen via the payload."""
    set_active("topaz")
    ctx = BeamlineContext(get("topaz"))
    assert ctx.angle_pv("omega") == "BL12:Mot:goniokm:omega"
    assert str(ctx.bob_screen).endswith("BL12_ADnED_2D_4x4.bob")

    corelli_ctx = BeamlineContext(get("corelli"))
    assert corelli_ctx.bob_screen is None
    set_active("topaz")


# ---------- technique / technique_config consistency ----------


def test_bare_spec_defaults_to_single_crystal() -> None:
    spec = BeamlineSpec(id="bare", display_name="Bare")
    assert spec.technique == "single_crystal"
    assert isinstance(spec.technique_config, SingleCrystalConfig)


def test_technique_field_synced_from_payload() -> None:
    spec = BeamlineSpec(id="s", display_name="S", technique_config=SansConfig())
    # ``technique`` is derived from ``technique_config.kind``.
    assert spec.technique == "sans"


def test_mismatched_technique_kwarg_is_corrected() -> None:
    """``technique_config.kind`` wins over an out-of-sync ``technique`` kwarg."""
    spec = BeamlineSpec(
        id="m",
        display_name="M",
        technique="sans",
        technique_config=SingleCrystalConfig(),
    )
    assert spec.technique == "single_crystal"


# ---------- discriminator parsing + narrowing ----------


def test_discriminator_parses_dict_payload() -> None:
    spec = BeamlineSpec(
        id="p",
        display_name="P",
        technique_config=cast(
            "SingleCrystalConfig | SansConfig",
            {"kind": "sans", "mantid_instrument_name": "USANS"},
        ),
    )
    assert isinstance(spec.technique_config, SansConfig)
    assert spec.technique == "sans"
    assert spec.technique_config.mantid_instrument_name == "USANS"


def test_single_crystal_accessor_rejects_non_sc_payload() -> None:
    spec = BeamlineSpec(id="q", display_name="Q", technique_config=SansConfig())
    with pytest.raises(TypeError):
        _ = spec.single_crystal


def test_sans_config_stub_fields_default_none() -> None:
    cfg = SansConfig()
    assert cfg.kind == "sans"
    assert cfg.mantid_instrument_name is None
    assert cfg.default_q_range is None
    assert cfg.transmission_monitor_pv is None
    assert cfg.live_stream_url is None
