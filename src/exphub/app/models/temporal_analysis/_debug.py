"""Debug tracing for the live-data path.

The live loop runs a full Mantid pipeline every ~40s and used to emit
~50+ multi-line separator prints per cycle, which blocked the asyncio
event loop on slow terminals. Flip ``CRYSTALPILOT_DEBUG=1`` to re-enable
that tracing while investigating issues.
"""

from __future__ import annotations

import os
from typing import Any

DEBUG_LIVE = bool(os.environ.get("CRYSTALPILOT_DEBUG"))


def trace(*args: Any) -> None:
    if DEBUG_LIVE:
        print(*args)
