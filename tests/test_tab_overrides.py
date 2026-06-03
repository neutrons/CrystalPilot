"""Tab-overrides contract test.

Locks the per-beamline tab-factory contract used by
``tab_content_panel.py``. As of P0:

- ``TabOverrides()`` exposes 5 slots; each defaults to ``None``.
- A registered beamline can supply a callable factory in any slot.
- The dispatcher pattern: ``factory = active().tabs.<slot>``; if ``None``,
  show the placeholder; else call ``factory(view_model)``.

The multi-technique plan (``MULTI_TECHNIQUE_PLAN.md``) generalises this
contract across all 5 slots. The slots are technique-neutral and TabKey-aligned
(``ipts``/``live``/``steering``/``status``/``analysis``); each technique manifest
maps a ``TabKey`` to the slot name it reads. This test exercises the slot
mechanism in isolation so the generalisation lands on a covered seam.
"""

from __future__ import annotations

import pytest

from exphub.core.beamline import active, list_ids
from exphub.core.beamline.spec import TabOverrides

# ---------- TabOverrides intrinsic shape ----------

def test_tab_overrides_default_all_none() -> None:
    overrides = TabOverrides()
    assert overrides.ipts is None
    assert overrides.steering is None
    assert overrides.live is None
    assert overrides.status is None
    assert overrides.analysis is None


def test_tab_overrides_accepts_callable_in_any_slot() -> None:
    def factory(_vm):  # type: ignore[no-untyped-def]
        return object()

    overrides = TabOverrides(
        ipts=factory,
        steering=factory,
        live=factory,
        status=factory,
        analysis=factory,
    )
    for slot in ("ipts", "steering", "live", "status", "analysis"):
        assert callable(getattr(overrides, slot))


def test_tab_overrides_slot_names_are_stable() -> None:
    """Adding/removing/renaming slots breaks every beamline plug-in and the manifest; pin the set."""
    assert set(TabOverrides.model_fields) == {
        "ipts",
        "steering",
        "live",
        "status",
        "analysis",
    }


# ---------- Registered-beamline behaviour ----------

def test_topaz_supplies_css_status_factory() -> None:
    """TOPAZ is the reference per-beamline tab implementation."""
    if "topaz" not in list_ids():
        pytest.skip("TOPAZ beamline plug-in not registered")
    from exphub.core.beamline import get
    topaz = get("topaz")
    assert callable(topaz.tabs.status), (
        "TOPAZ should ship a status factory — the reference impl."
    )


def test_corelli_does_not_supply_css_status_factory() -> None:
    """CORELLI uses the placeholder fall-through — proves the contract works."""
    if "corelli" not in list_ids():
        pytest.skip("CORELLI beamline plug-in not registered")
    from exphub.core.beamline import get
    corelli = get("corelli")
    assert corelli.tabs.status is None, (
        "CORELLI should leave status as None to exercise the placeholder."
    )


def test_dispatcher_lookup_pattern() -> None:
    """The tab-content-panel dispatcher reads exactly this surface."""
    spec = active()
    tabs = spec.tabs
    # The 4 not-yet-dispatched slots must still be readable as either
    # None or callable so the future P3 dispatcher can fan out uniformly.
    for slot in ("ipts", "steering", "live", "status", "analysis"):
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
    from exphub.app.views.placeholder_tab import PlaceholderTab
    from exphub.core.beamline import TabKey, get_technique

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


def test_all_five_slots_resolve_to_callable_for_topaz() -> None:
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


def test_topaz_slots_route_to_expected_sources() -> None:
    """TOPAZ slot routing.

    Tabs 1-3 from technique defaults, STATUS from its status override,
    ANALYSIS from the opted-in optional default.
    """
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
    # STATUS resolves to TOPAZ's own status override.
    assert resolved[TabKey.STATUS] is topaz.tabs.status
    # ANALYSIS resolves to the opted-in technique optional default.
    assert TabKey.ANALYSIS in topaz.optional_tabs
    assert resolved[TabKey.ANALYSIS] is technique.optional_tab_defaults[TabKey.ANALYSIS]


def test_corelli_analysis_resolves_to_real_data_analysis_factory() -> None:
    """CORELLI's ANALYSIS slot (tab 6) must render the real Data Analysis view, not the placeholder.

    The ANALYSIS slot has no unconditional technique default; CORELLI neither
    opts into the optional default (``optional_tabs``) nor would inherit one,
    so without its own ``tabs.analysis`` factory it would fall through to
    the placeholder. Pin that CORELLI ships the factory and that the dispatcher
    resolves ANALYSIS to it (P3 deliverable 3).
    """
    if "corelli" not in list_ids():
        pytest.skip("CORELLI beamline plug-in not registered")
    from exphub.core.beamline import TabKey, get, get_technique

    corelli = get("corelli")
    technique = get_technique("single_crystal")

    # CORELLI supplies its own ANALYSIS factory via the override slot.
    assert callable(corelli.tabs.analysis), (
        "CORELLI should ship an analysis (ANALYSIS / tab 6) factory so the "
        "slot does not regress to the placeholder."
    )

    resolved = _resolve_all_slots(corelli)
    analysis_factory = resolved[TabKey.ANALYSIS]
    # Resolves to CORELLI's own override (highest precedence)...
    assert analysis_factory is corelli.tabs.analysis
    # ...which is the real factory, not the placeholder closure.
    assert "factory" not in getattr(analysis_factory, "__name__", "")
    # CORELLI does not rely on the opt-in path for this slot.
    assert TabKey.ANALYSIS not in corelli.optional_tabs
    assert analysis_factory is not technique.optional_tab_defaults[TabKey.ANALYSIS]


def test_corelli_data_analysis_factory_builds_real_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invoking CORELLI's ANALYSIS factory constructs the shared ``DataAnalysisView``.

    Proves the wrapper wires to the real view, not a placeholder. The view's
    ``create_ui`` needs a live trame layout context, so we stub it out and only
    assert the view-model is bound.
    """
    if "corelli" not in list_ids():
        pytest.skip("CORELLI beamline plug-in not registered")
    from exphub.core.beamline import get
    from exphub.techniques.single_crystal.views import data_analysis as da_mod

    built = {}

    class _FakeBind:
        def connect(self, _name: str) -> None:  # noqa: D401 - test stub
            built["connected"] = _name

    class _FakeVM:
        dataanalysis_bind = _FakeBind()

    # The real DataAnalysisView.create_ui requires a trame layout context;
    # neutralise it so the test runs headless while still exercising __init__.
    monkeypatch.setattr(da_mod.DataAnalysisView, "create_ui", lambda self: None)

    factory = get("corelli").tabs.analysis
    assert factory is not None
    view = factory(_FakeVM())

    assert isinstance(view, da_mod.DataAnalysisView)
    assert built.get("connected") == "model_dataanalysis"


def test_placeholder_fall_through_when_not_opted_in() -> None:
    """A slot with no override/default/opt-in resolves to a callable placeholder closure.

    The closure is not None and not a technique/override factory.
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

def test_topaz_factory_signature_is_one_positional() -> None:
    """Factories receive the active MainViewModel as a single positional argument.

    The P3 dispatcher relies on this; lock it now so a beamline can't ship a
    multi-arg factory that the dispatcher fails to call.
    """
    if "topaz" not in list_ids():
        pytest.skip("TOPAZ beamline plug-in not registered")
    import inspect

    from exphub.core.beamline import get
    factory = get("topaz").tabs.status
    assert factory is not None
    sig = inspect.signature(factory)
    positional = [p for p in sig.parameters.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    # Factories take exactly one positional (the view-model); kwargs OK.
    assert len(positional) == 1, (
        f"TOPAZ status factory should take one positional argument "
        f"(the view-model); got signature {sig}"
    )
