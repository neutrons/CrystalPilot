"""Main Application."""

import os
import sys


def main() -> None:
    # Must be set before wslink is imported (it reads MAX_MSG_SIZE at module
    # level).  Large 2D detector PVs (e.g. a 1105×1105 heatmap) produce
    # ~5-8 MB trame state flushes; wslink's default 4 MB chunk limit splits
    # these into 2+ chunks.  Setting the limit above the largest expected
    # message keeps every wslink message as a single chunk, avoiding the
    # partial-message reassembly path that triggers ValueError in
    # chunking.py on the Instrument Status tab.
    os.environ.setdefault("WSLINK_MAX_MSG_SIZE", str(32 * 1024 * 1024))  # 32 MB

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
