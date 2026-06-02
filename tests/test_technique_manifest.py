"""Tests for the technique-manifest layer (P1.a).

See ``MULTI_TECHNIQUE_PLAN.md``. P1.a introduces, additively, the
technique-family plug-in surface above beamlines:

- a lazily-discovered technique registry
- a single-crystal manifest declaring tabs 1-3 (lazy-importing the existing
  app views) plus the tab label/alias and bridged-submodel contract

No app/core code has moved yet, so these tests pin the new surface without
touching the still-flat composition.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

import exphub.beamlines  # noqa: F401 — registers beamlines
from exphub.core.beamline import (
    TabKey,
    TechniqueManifest,
    active_technique,
    get_technique,
    set_active,
)
from exphub.core.beamline.technique import _reset_for_tests

# ---------- registry + lazy discovery ----------


def test_get_technique_lazily_discovers_single_crystal():
    _reset_for_tests()
    manifest = get_technique("single_crystal")
    assert isinstance(manifest, TechniqueManifest)
    assert manifest.id == "single_crystal"


def test_get_technique_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        get_technique("does_not_exist")


def test_active_technique_follows_active_beamline():
    set_active("topaz")
    assert active_technique().id == "single_crystal"
    set_active("corelli")
    assert active_technique().id == "single_crystal"
    set_active("topaz")


# ---------- TabKey contract ----------


def test_tabkey_values_are_stable():
    # The dispatcher + agent depend on these exact string ids; renaming any is
    # a breaking change.
    assert [k.value for k in TabKey] == [
        "ipts",
        "live",
        "steering",
        "status",
        "analysis",
    ]


# ---------- single-crystal manifest shape ----------


def test_single_crystal_declares_default_tabs_1_to_3():
    manifest = get_technique("single_crystal")
    assert set(manifest.default_tabs) == {TabKey.IPTS, TabKey.LIVE, TabKey.STEERING}
    # Tabs 4-5 have no technique default (fall through to beamline/placeholder).
    assert TabKey.STATUS not in manifest.default_tabs
    assert TabKey.ANALYSIS not in manifest.default_tabs


def test_default_tab_factories_take_one_positional_arg():
    """Each factory is called with the active view-model (the TabFactory protocol)."""
    manifest = get_technique("single_crystal")
    for key, factory in manifest.default_tabs.items():
        assert callable(factory), key
        params = list(inspect.signature(factory).parameters.values())
        positional = [
            p
            for p in params
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        assert len(positional) == 1, key


def test_manifest_has_labels_for_all_five_tabs():
    manifest = get_technique("single_crystal")
    assert set(manifest.tab_labels) == set(TabKey)


def test_tab_aliases_resolve_to_valid_tab_keys():
    manifest = get_technique("single_crystal")
    assert manifest.tab_aliases["temporal_analysis"] is TabKey.LIVE
    assert manifest.tab_aliases["angle_plan"] is TabKey.STEERING
    assert all(isinstance(v, TabKey) for v in manifest.tab_aliases.values())


# ---------- invariant #3: bridged_submodels exist on the root model ----------


def test_bridged_submodels_exist_on_main_model():
    from exphub.app.models.main_model import MainModel

    manifest = get_technique("single_crystal")
    model = MainModel()
    for name in manifest.bridged_submodels:
        assert hasattr(model, name), name


def test_manifest_is_frozen():
    manifest = get_technique("single_crystal")
    with pytest.raises(ValidationError):
        manifest.id = "mutated"  # type: ignore[misc]
