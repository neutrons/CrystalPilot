"""Fall-through placeholder tab content.

When a tab slot has no technique default and no beamline-provided factory
(typically the STATUS / ANALYSIS slots for a beamline that has not yet shipped
its own tabs), the manifest-driven dispatcher in :mod:`tab_content_panel`
renders this view instead of leaving the tab blank.

It shows a single informational alert plus an optional row of buttons linking
to external tools (e.g. a Mantid GUI or a web reduction tool). Both the message
and the link list come from the active :class:`BeamlineSpec`
(``placeholder_messages`` / ``placeholder_links``).
"""

from __future__ import annotations

from nova.trame.view.layouts import HBoxLayout, VBoxLayout
from trame.widgets import vuetify3 as vuetify


class PlaceholderTab:
    """Render a simple alert + external-link buttons for an unconfigured tab.

    :param message: Informational text shown in the alert. Falls back to a
        generic "not configured" message when empty.
    :param external_links: ``(label, url)`` pairs rendered as link buttons that
        open in a new tab. Empty list renders no buttons.
    """

    def __init__(
        self,
        message: str | None = None,
        external_links: list[tuple[str, str]] | None = None,
    ) -> None:
        self.message = message or "This tab is not configured for the active beamline."
        self.external_links = external_links or []
        self.create_ui()

    def create_ui(self) -> None:
        with VBoxLayout(gap="0.5em"):
            vuetify.VAlert(
                text=self.message,
                type="info",
                variant="tonal",
            )
            if self.external_links:
                with HBoxLayout(gap="0.5em", valign="center"):
                    for label, url in self.external_links:
                        vuetify.VBtn(
                            label,
                            color="primary",
                            href=url,
                            raw_attrs=['target="_blank"'],
                        )
