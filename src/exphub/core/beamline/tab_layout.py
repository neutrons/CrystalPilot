"""Per-beamline tab layout — the single source of truth for the tab strip shape.

Replaces the three places that used to hardcode the five-tab shape (the strip's
``VTab`` list in ``app/views/tabs_panel.py``, the dispatcher's ``_SLOTS`` tuple
in ``app/views/tab_content_panel.py``, and the ``_TAB_KEY_TO_INT`` map in
``app/view_models/app_shell.py``) with one layout resolved per active beamline.

A :class:`TabGroup` is one rendered tab. ``covers`` is the set of
:class:`~exphub.core.beamline.technique.TabKey` slots that tab shows: one key is
an ordinary tab; several keys are a *combined* tab that stacks those slots'
content in one scrollable column.

A beamline that wants a non-default shape (e.g. USANS merging
IPTS + LIVE + STEERING into one tab) sets :attr:`BeamlineSpec.tab_layout`.
Every other beamline leaves it ``None`` and gets :func:`default_layout`, which
reproduces the historical five single-key tabs (ids 1/2/3/5/6 — the gap at 4 is
historical) with labels read from the technique manifest. The default is
byte-identical to the old hardcoded strip for the shipped single-crystal
beamlines, so they are untouched.
"""

from __future__ import annotations

from dataclasses import dataclass

from .technique import TabKey, TechniqueManifest


@dataclass(frozen=True)
class TabGroup:
    """One tab in the strip.

    ``id`` is the integer the trame ``v_model="controls.active_tab"`` /
    ``v_if="controls.active_tab == N"`` predicates address (kept as the legacy
    1/2/3/5/6 ids for the default layout so single-crystal output does not move).
    ``label`` is the ``VTab`` text. ``covers`` lists the :class:`TabKey` slots
    this tab renders — one key for a normal tab, several for a combined tab.
    """

    id: int
    label: str
    covers: tuple[TabKey, ...]


TabLayout = tuple[TabGroup, ...]
"""An ordered tuple of :class:`TabGroup` — the full tab strip for a beamline."""


# Canonical default tab order + legacy integer ids. The gap at 4 is historical
# (there has never been a tab 4); preserved so the default layout's ids match
# every existing ``active_tab`` reference and persisted UI state.
_DEFAULT_ORDER: tuple[tuple[TabKey, int], ...] = (
    (TabKey.IPTS, 1),
    (TabKey.LIVE, 2),
    (TabKey.STEERING, 3),
    (TabKey.STATUS, 5),
    (TabKey.ANALYSIS, 6),
)

# Fallback labels if a manifest omits one (every shipped manifest sets all five).
_FALLBACK_LABELS: dict[TabKey, str] = {
    TabKey.IPTS: "IPTS Info",
    TabKey.LIVE: "Live Data Processing",
    TabKey.STEERING: "Experiment Steering",
    TabKey.STATUS: "Instrument Status",
    TabKey.ANALYSIS: "Data Analysis",
}


def default_layout(manifest: TechniqueManifest) -> TabLayout:
    """The historical five-tab layout: one single-key tab per slot.

    Ids 1/2/3/5/6; labels come from ``manifest.tab_labels`` (this is what finally
    wires the manifest labels into the strip), falling back to the legacy strings.
    """
    return tuple(
        TabGroup(id=tab_id, label=manifest.tab_labels.get(key, _FALLBACK_LABELS[key]), covers=(key,))
        for key, tab_id in _DEFAULT_ORDER
    )


def active_layout() -> TabLayout:
    """Resolve the active beamline's tab layout.

    A beamline's own ``tab_layout`` (set on its :class:`BeamlineSpec`) wins;
    otherwise the active technique's :func:`default_layout`.
    """
    from .registry import active
    from .technique import active_technique

    spec_layout = getattr(active(), "tab_layout", None)
    if spec_layout:
        return tuple(spec_layout)
    return default_layout(active_technique())


def tab_key_to_int(tab: "TabKey | int | str") -> int:
    """Translate a :class:`TabKey` (or its str value) to the active layout's tab id.

    A merged ``TabKey`` resolves to its combined tab's id, so agent / phase
    navigation that addresses IPTS / LIVE / STEERING all land on the one visible
    tab when a beamline merges them. Ints pass through unchanged.
    """
    if isinstance(tab, int):
        return tab
    key = getattr(tab, "value", tab)
    layout = active_layout()
    for group in layout:
        if any(covered.value == key for covered in group.covers):
            return group.id
    return layout[0].id if layout else 1


def label_for(key: TabKey) -> str:
    """Label for a single :class:`TabKey`, from the active technique's manifest.

    Used as the section header for each slot stacked inside a combined tab.
    """
    from .technique import active_technique

    return active_technique().tab_labels.get(key, _FALLBACK_LABELS[key])
