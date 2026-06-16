"""Tab-layout resolution contract — the per-beamline tab strip shape.

``active_layout()`` is the single source of truth the strip
(``tabs_panel.py``) and the dispatcher (``tab_content_panel.py``) both read,
replacing the old hardcoded five-tab list. This pins:

- the default (no per-beamline override) layout reproduces the historical five
  single-key tabs — ids 1/2/3/5/6, labels from the manifest — for the shipped
  single-crystal beamlines, so they are byte-identical, and
- ``tab_key_to_int`` maps each TabKey to its tab's id (identity for the default).

USANS' merged layout is exercised in
``tests/techniques/sans/test_sans_tab_layout.py``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from exphub.core.beamline import set_active
from exphub.core.beamline.tab_layout import active_layout, default_layout, tab_key_to_int
from exphub.core.beamline.technique import TabKey, get_technique


@pytest.fixture(autouse=True)
def _restore_default() -> Iterator[None]:
    """Each test sets its own active beamline; restore the TOPAZ default after."""
    yield
    set_active("topaz")


def test_single_crystal_default_layout_is_five_single_key_tabs() -> None:
    set_active("topaz")
    layout = active_layout()
    assert [g.id for g in layout] == [1, 2, 3, 5, 6]
    assert all(len(g.covers) == 1 for g in layout)
    assert [g.covers[0] for g in layout] == [
        TabKey.IPTS,
        TabKey.LIVE,
        TabKey.STEERING,
        TabKey.STATUS,
        TabKey.ANALYSIS,
    ]


def test_default_layout_labels_match_the_legacy_strip() -> None:
    """Labels now come from the manifest; for single-crystal they equal the old hardcoded strip."""
    set_active("topaz")
    labels = [g.label for g in active_layout()]
    assert labels == [
        "IPTS Info",
        "Live Data Processing",
        "Experiment Steering",
        "Instrument Status",
        "Data Analysis",
    ]


def test_single_crystal_tab_key_to_int_is_identity() -> None:
    set_active("topaz")
    assert tab_key_to_int(TabKey.IPTS) == 1
    assert tab_key_to_int(TabKey.LIVE) == 2
    assert tab_key_to_int(TabKey.STEERING) == 3
    assert tab_key_to_int(TabKey.STATUS) == 5
    assert tab_key_to_int(TabKey.ANALYSIS) == 6
    assert tab_key_to_int(2) == 2  # ints pass through


def test_corelli_uses_the_default_layout_too() -> None:
    set_active("corelli")
    assert [g.id for g in active_layout()] == [1, 2, 3, 5, 6]


def test_default_layout_reads_sans_labels() -> None:
    """The SANS manifest's labels (e.g. LIVE='Live Data') flow into the default layout."""
    sans = get_technique("sans")
    labels = {g.covers[0]: g.label for g in default_layout(sans)}
    assert labels[TabKey.LIVE] == "Live Data"
