"""USANS merged-tab layout — the beamline-specific tab shape.

USANS folds its three workflow tabs (IPTS info, I(Q) reduction, experiment
steering) into one combined tab while keeping STATUS / ANALYSIS separate. This
pins both the strip shape and the navigation contract that keeps the agent /
SANS phases working: a merged TabKey must resolve to the combined tab's id.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from exphub.core.beamline import set_active
from exphub.core.beamline.tab_layout import active_layout, tab_key_to_int
from exphub.core.beamline.technique import TabKey


@pytest.fixture(autouse=True)
def _usans_active() -> Iterator[None]:
    set_active("usans")
    yield
    set_active("topaz")


def test_usans_merges_first_three_tabs_into_one() -> None:
    layout = active_layout()
    # One combined tab (id 1) covering IPTS+LIVE+STEERING, then STATUS + ANALYSIS.
    assert [g.id for g in layout] == [1, 5, 6]
    combined = layout[0]
    assert combined.covers == (TabKey.IPTS, TabKey.LIVE, TabKey.STEERING)
    assert combined.label == "Experiment Setup & Steering"
    # STATUS / ANALYSIS stay as their own single-key tabs.
    assert layout[1].covers == (TabKey.STATUS,)
    assert layout[2].covers == (TabKey.ANALYSIS,)


def test_usans_nav_to_any_merged_key_lands_on_the_combined_tab() -> None:
    # Agent / SANS-phase navigation addresses tabs by TabKey; all three merged
    # keys must resolve to the one visible combined tab (id 1).
    assert tab_key_to_int(TabKey.IPTS) == 1
    assert tab_key_to_int(TabKey.LIVE) == 1
    assert tab_key_to_int(TabKey.STEERING) == 1
    # STATUS / ANALYSIS keep their own ids.
    assert tab_key_to_int(TabKey.STATUS) == 5
    assert tab_key_to_int(TabKey.ANALYSIS) == 6


def test_topaz_layout_is_unaffected_by_usans_override() -> None:
    """Switching back to a single-crystal beamline restores the default five tabs."""
    set_active("topaz")
    assert [g.id for g in active_layout()] == [1, 2, 3, 5, 6]
