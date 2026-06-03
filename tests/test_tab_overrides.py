"""Tab-overrides contract test.

Locks the per-beamline tab-factory contract used by
``tab_content_panel.py``. As of P0:

- ``TabOverrides()`` exposes 5 slots; each defaults to ``None``.
- A registered beamline can supply a callable factory in any slot.
- The dispatcher pattern: ``factory = active().tabs.<slot>``; if ``None``,
  show the placeholder; else call ``factory(view_model)``.

The multi-technique plan (``MULTI_TECHNIQUE_PLAN.md``) generalises this
contract across all 5 slots in P3. Until then, only ``css_status`` is
consulted by the live dispatcher; this test exercises the slot mechanism
in isolation so the generalisation lands on a covered seam.
"""

from __future__ import annotations

import pytest

from exphub.core.beamline import active, list_ids
from exphub.core.beamline.spec import TabOverrides


# ---------- TabOverrides intrinsic shape ----------

def test_tab_overrides_default_all_none():
    overrides = TabOverrides()
    assert overrides.experiment_info is None
    assert overrides.angle_plan is None
    assert overrides.temporal_analysis is None
    assert overrides.css_status is None
    assert overrides.data_analysis is None


def test_tab_overrides_accepts_callable_in_any_slot():
    def factory(_vm):  # type: ignore[no-untyped-def]
        return object()

    overrides = TabOverrides(
        experiment_info=factory,
        angle_plan=factory,
        temporal_analysis=factory,
        css_status=factory,
        data_analysis=factory,
    )
    for slot in ("experiment_info", "angle_plan", "temporal_analysis",
                 "css_status", "data_analysis"):
        assert callable(getattr(overrides, slot))


def test_tab_overrides_slot_names_are_stable():
    """Adding/removing/renaming slots is a breaking change for every
    beamline plug-in and the manifest. Pin the set."""
    assert set(TabOverrides.model_fields) == {
        "experiment_info",
        "angle_plan",
        "temporal_analysis",
        "css_status",
        "data_analysis",
    }


# ---------- Registered-beamline behaviour ----------

def test_topaz_supplies_css_status_factory():
    """TOPAZ is the reference per-beamline tab implementation."""
    if "topaz" not in list_ids():
        pytest.skip("TOPAZ beamline plug-in not registered")
    from exphub.core.beamline import get
    topaz = get("topaz")
    assert callable(topaz.tabs.css_status), (
        "TOPAZ should ship a css_status factory — the reference impl."
    )


def test_corelli_does_not_supply_css_status_factory():
    """CORELLI uses the placeholder fall-through — proves the contract works."""
    if "corelli" not in list_ids():
        pytest.skip("CORELLI beamline plug-in not registered")
    from exphub.core.beamline import get
    corelli = get("corelli")
    assert corelli.tabs.css_status is None, (
        "CORELLI should leave css_status as None to exercise the placeholder."
    )


def test_dispatcher_lookup_pattern():
    """The tab-content-panel dispatcher reads exactly this surface."""
    spec = active()
    tabs = spec.tabs
    # The 4 not-yet-dispatched slots must still be readable as either
    # None or callable so the future P3 dispatcher can fan out uniformly.
    for slot in ("experiment_info", "angle_plan", "temporal_analysis",
                 "css_status", "data_analysis"):
        value = getattr(tabs, slot)
        assert value is None or callable(value), (
            f"TabOverrides.{slot} on {spec.id!r} must be None or callable; "
            f"got {type(value).__name__}"
        )


# ---------- Manifest-driven dispatcher resolution (P3.1) ----------

def _resolve_all_slots(spec):  # type: ignore[no-untyped-def]
    """Resolve every tab slot exactly as ``TabContentPanel`` does.

    Mirrors ``tab_content_panel._resolve_factory`` without constructing the
    trame UI: beamline override → technique default → opted-in optional default
    → placeholder closure. Returns ``{TabKey: factory}`` (always callable).
    """
    from exphub.core.beamline import TabKey, get_technique
    from exphub.app.views.placeholder_tab import PlaceholderTab

    technique = get_technique(spec.technique)
    resolved = {}
    for key in TabKey:
        override_attr = technique.tab_override_slots.get(key)
        factory = None
        if override_attr is not None:
            factory = getattr(spec.tabs, override_attr, None)
        if factory is None:
            factory = technique.default_tabs.get(key)
        if factory is None and key in spec.optional_tabs:
            factory = technique.optional_tab_defaults.get(key)
        if factory is None:
            message = spec.placeholder_messages.get(key)
            links = spec.placeholder_links.get(key)

            def factory(_vm, _m=message, _l=links):  # type: ignore[no-untyped-def]
                return PlaceholderTab(message=_m, external_links=_l)

        resolved[key] = factory
    return resolved


def test_all_five_slots_resolve_to_callable_for_topaz():
    """Every TabKey resolves to a one-argument factory via the manifest."""
    if "topaz" not in list_ids():
        pytest.skip("TOPAZ beamline plug-in not registered")
    import inspect
    from exphub.core.beamline import TabKey, get

    resolved = _resolve_all_slots(get("topaz"))
    assert set(resolved) == set(TabKey)
    for key, factory in resolved.items():
        assert callable(factory), key
        positional = [
            p for p in inspect.signature(factory).parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        assert len(positional) == 1, key


def test_topaz_slots_route_to_expected_sources():
    """TOPAZ: tabs 1-3 from technique defaults, STATUS from its css_status
    override, ANALYSIS from the opted-in optional default."""
    if "topaz" not in list_ids():
        pytest.skip("TOPAZ beamline plug-in not registered")
    from exphub.core.beamline import TabKey, get, get_technique

    topaz = get("topaz")
    technique = get_technique("single_crystal")
    resolved = _resolve_all_slots(topaz)

    # Tabs 1-3 come straight from the technique defaults.
    assert resolved[TabKey.IPTS] is technique.default_tabs[TabKey.IPTS]
    assert resolved[TabKey.LIVE] is technique.default_tabs[TabKey.LIVE]
    assert resolved[TabKey.STEERING] is technique.default_tabs[TabKey.STEERING]
    # STATUS resolves to TOPAZ's own css_status override.
    assert resolved[TabKey.STATUS] is topaz.tabs.css_status
    # ANALYSIS resolves to the opted-in technique optional default.
    assert TabKey.ANALYSIS in topaz.optional_tabs
    assert resolved[TabKey.ANALYSIS] is technique.optional_tab_defaults[TabKey.ANALYSIS]


def test_placeholder_fall_through_when_not_opted_in():
    """A slot with no override, no default, and no opt-in resolves to a
    callable placeholder closure (not None, not a technique/override factory).

    The closure builds a ``PlaceholderTab``; we don't invoke it here because
    that requires a live trame server context. We instead assert it is none of
    the real factories, i.e. the placeholder branch was taken.
    """
    from exphub.core.beamline import (
        BeamlineSpec,
        SingleCrystalConfig,
        TabKey,
        get_technique,
    )

    spec = BeamlineSpec(
        id="_test_placeholder",
        display_name="test",
        technique_config=SingleCrystalConfig(),
    )
    resolved = _resolve_all_slots(spec)
    technique = get_technique("single_crystal")

    # STATUS has no technique default and no override/opt-in → placeholder.
    status_factory = resolved[TabKey.STATUS]
    assert callable(status_factory)
    assert status_factory not in technique.default_tabs.values()
    assert status_factory not in technique.optional_tab_defaults.values()
    # ANALYSIS is also a placeholder here (this bare spec opts into nothing).
    assert TabKey.ANALYSIS not in spec.optional_tabs
    analysis_factory = resolved[TabKey.ANALYSIS]
    assert callable(analysis_factory)
    assert analysis_factory is not technique.optional_tab_defaults[TabKey.ANALYSIS]
    # The closure's qualified name reflects its placeholder origin.
    assert "factory" in status_factory.__name__


# ---------- Future-proofing for the multi-technique dispatcher ----------

def test_topaz_factory_signature_is_one_positional():
    """Factories receive the active MainViewModel as a single positional
    argument. The P3 dispatcher relies on this; lock it now so a beamline
    can't ship a multi-arg factory that the dispatcher fails to call."""
    if "topaz" not in list_ids():
        pytest.skip("TOPAZ beamline plug-in not registered")
    import inspect
    from exphub.core.beamline import get
    factory = get("topaz").tabs.css_status
    assert factory is not None
    sig = inspect.signature(factory)
    positional = [p for p in sig.parameters.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    # Factories take exactly one positional (the view-model); kwargs OK.
    assert len(positional) == 1, (
        f"TOPAZ css_status factory should take one positional argument "
        f"(the view-model); got signature {sig}"
    )
