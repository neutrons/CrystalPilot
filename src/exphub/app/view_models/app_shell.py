"""App-shell ViewModel: the technique-agnostic window chrome.

Owns tab navigation, the beamline selector, the informational snackbar, and
the under-development / uninterruptable dialogs — everything that is *not*
specific to a particular technique. The single-crystal experiment-steering
concerns live in
``techniques/single_crystal/view_models/steering.py``.

Extracted from the former ``MainViewModel`` during the multi-technique
refactor (P2.16).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Dict

from nova.mvvm.interface import BindingInterface
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ...core.beamline import TabKey

_DEBUG = bool(os.environ.get("CRYSTALPILOT_DEBUG"))


def _trace(*args: Any) -> None:
    if _DEBUG:
        print(*args)


def _default_beamline_id() -> str:
    """Pick the active beamline's id at view-state construction time."""
    try:
        from ...core.beamline import active as _active_beamline

        return _active_beamline().id
    except Exception:
        return ""


def _default_beamline_options() -> list[dict]:
    """Build the ``[{value, title}]`` list for the selector."""
    try:
        from ...core.beamline import get as _get
        from ...core.beamline import list_ids as _list_ids

        return [{"value": bid, "title": _get(bid).display_name} for bid in _list_ids()]
    except Exception:
        return []


# TabKey value -> legacy integer tab number used by the trame dispatcher's
# v_if/v_show predicates. Keyed by the enum's string value so this module
# needs no runtime import of TabKey.
_TAB_KEY_TO_INT: dict[str, int] = {
    "ipts": 1, "live": 2, "steering": 3, "status": 5, "analysis": 6,
}


def _tab_to_int(tab: "TabKey | int | str") -> int:
    """Translate a TabKey (or its str value) to the dispatcher's int; pass ints through."""
    if isinstance(tab, int):
        return tab
    key = getattr(tab, "value", tab)  # TabKey -> "ipts"; plain str -> itself
    return _TAB_KEY_TO_INT.get(key, 1)


class AppShellViewState(BaseModel):
    """View state for the technique-agnostic application shell."""

    active_tab: int = Field(default=0)
    is_under_development: bool = Field(default=False)
    is_uninterruptable: bool = Field(default=False)
    beamline_id: str = Field(default_factory=_default_beamline_id)
    beamline_options: list[dict] = Field(default_factory=_default_beamline_options)
    beamline_switch_notice: str = Field(default="")
    beamline_switch_visible: bool = Field(default=False)


class AppShellViewModel:
    """ViewModel for the window chrome: tab strip, beamline selector, dialogs."""

    def __init__(self, binding: BindingInterface) -> None:
        self.view_state = AppShellViewState()
        # Track the last-known beamline so the view_state callback only triggers
        # a switch when the user actually picked a new option in the selector.
        self._last_beamline_id: str = self.view_state.beamline_id
        self.view_state_bind = binding.new_bind(
            self.view_state, callback_after_update=self.on_view_state_change
        )

    def on_view_state_change(self, results: Dict[str, Any]) -> None:
        """Detect user-driven changes to the shell view-state (beamline selector)."""
        if results.get("error"):
            print(f"view_state error in {results.get('errored')}")
            return
        if self.view_state.beamline_id != self._last_beamline_id:
            new_id = self.view_state.beamline_id
            self._last_beamline_id = new_id
            self.switch_beamline(new_id)

    def navigate_to_tab(self, tab: "TabKey | int") -> None:
        """Switch the active tab and push the change to the view.

        Accepts a :class:`TabKey` (preferred — the agent and the technique
        manifest speak TabKey) or the legacy integer tab number (translation
        shim). The trame dispatcher keys its v_if/v_show predicates on the int
        (1=IPTS Info, 2=Live Data Processing, 3=Experiment Steering,
        5=Instrument Status, 6=Data Analysis), so the TabKey is mapped here.
        """
        self.view_state.active_tab = _tab_to_int(tab)
        self.view_state_bind.update_in_view(self.view_state)

    def switch_beamline(self, beamline_id: str) -> None:
        """Activate a different beamline plug-in.

        Called either directly (e.g. tests) or by ``on_view_state_change``
        when the user picks a new option in the selector. Updates the
        registry so subsequent reads of ``active().<...>`` pick up the new
        beamline's PVs/paths/presets.

        Hard-bound resources — the EPICS ``.bob`` screen connected at
        MainApp construction, the agent's RAG index, and the auto-resolved
        model-field defaults already applied to existing instances — won't
        reload mid-session. A snackbar surfaces that note.
        """
        from ...core.beamline import set_active

        if not beamline_id:
            return
        try:
            spec = set_active(beamline_id)
        except KeyError as e:
            print(f"switch_beamline: {e}")
            return
        # Keep our cached id aligned so the next change_callback doesn't loop.
        self._last_beamline_id = spec.id
        self.view_state.beamline_id = spec.id
        self.view_state.beamline_switch_notice = (
            f"Switched to {spec.display_name}. Restart the app for the "
            "Instrument Status screen and EPICS subscriptions to fully reload."
        )
        self.view_state.beamline_switch_visible = True
        self._push_view_state()

    def notify(self, message: str) -> None:
        """Surface an informational message in the shell snackbar.

        Reuses the beamline-switch snackbar (rendered by TabsPanel) so a
        technique view-model can flag an event — e.g. the steering VM pausing
        the live-update loop — without owning its own snackbar widget.
        """
        self.view_state.beamline_switch_notice = message
        self.view_state.beamline_switch_visible = True
        self._push_view_state()

    def show_under_development_dialog(self) -> None:
        _trace("show_underdev")
        self._push_view_state()

    def close_under_development_dialog(self) -> None:
        _trace("hide_underdev")
        self.view_state.is_under_development = False
        self._push_view_state()

    def _push_view_state(self) -> None:
        self.view_state_bind.update_in_view(self.view_state)
