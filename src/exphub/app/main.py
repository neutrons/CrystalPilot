"""Main Application."""

import logging
import os
import sys
from collections.abc import Mapping

logger = logging.getLogger(__name__)


def _resolve_startup_beamline(argv: list[str], env: Mapping[str, str]) -> str | None:
    """Pick the beamline to activate at launch.

    Precedence: a ``--beamline=<id>`` (or ``beamline=<id>``) CLI argument wins,
    then the ``CRYSTALPILOT_BEAMLINE`` environment variable, else ``None`` to use
    the registry default (the first-registered beamline).

    This is the restart-time picker the beamline selector's "restart to switch
    technique families" banner refers to: a beamline of a *different* technique
    family (e.g. a SANS beamline while a single-crystal beamline is the registry
    default) can only be entered this way, because live cross-technique switching
    is gated in v1.
    """
    for arg in argv:
        if arg.startswith("--beamline=") or arg.startswith("beamline="):
            return arg.split("=", 1)[1].strip() or None
    return (env.get("CRYSTALPILOT_BEAMLINE") or "").strip() or None


def _activate_startup_beamline(argv: list[str], env: Mapping[str, str]) -> None:
    """Resolve and apply the startup beamline to the registry, if one is set.

    Unknown ids are logged and ignored so launch falls back to the default
    rather than crashing.
    """
    chosen = _resolve_startup_beamline(argv, env)
    if not chosen:
        return
    from ..core.beamline import list_ids, set_active

    try:
        spec = set_active(chosen)
        logger.info("Startup beamline set to %r (technique=%s)", spec.id, spec.technique)
    except KeyError:
        logger.warning(
            "Unknown startup beamline %r; known: %s. Using registry default.",
            chosen,
            list_ids(),
        )


def main() -> None:
    # Fail loud if launched under a non-canonical package name (e.g.
    # ``python -m src.exphub.app``). That imports a SECOND copy of the package
    # with separate module state, so registry/technique discovery populates one
    # copy while the running code reads the other — beamline selection silently
    # breaks. Always launch as ``python -m exphub.app`` (what ``pixi run app`` does).
    if __package__ and not __package__.startswith("exphub"):
        logger.warning(
            "CrystalPilot launched as %r, not 'exphub.app' — this double-imports "
            "the package and breaks beamline/technique discovery. "
            "Run 'python -m exphub.app' (or 'pixi run app').",
            __package__,
        )

    # Must be set before wslink is imported (it reads MAX_MSG_SIZE at module
    # level).  Large 2D detector PVs (e.g. a 1105×1105 heatmap) produce
    # ~5-8 MB trame state flushes; wslink's default 4 MB chunk limit splits
    # these into 2+ chunks.  Setting the limit above the largest expected
    # message keeps every wslink message as a single chunk, avoiding the
    # partial-message reassembly path that triggers ValueError in
    # chunking.py on the Instrument Status tab.
    os.environ.setdefault("WSLINK_MAX_MSG_SIZE", str(32 * 1024 * 1024))  # 32 MB

    # Select the active beamline BEFORE building the app: MainApp() reads
    # active() at construction time, so a non-default (e.g. a cross-technique)
    # beamline must be chosen here, not via the runtime selector.
    _activate_startup_beamline(sys.argv[1:], os.environ)

    kwargs = {}
    from .views.main_view import MainApp

    app = MainApp()
    for arg in sys.argv[2:]:
        try:
            key, value = arg.split("=")
            kwargs[key] = int(value)
        except Exception:
            pass
    app.server.start(**kwargs)
