"""Framework-agnostic EIC integration (vendored client + control model).

The EIC (External Instrument Control) pipeline is shared by every technique:
:class:`EICControlModel` owns the authentication / submission / polling /
abort plumbing and submits *pre-built* table-scan jobs, while the vendored
:class:`EICClient` handles the HTTP/OAuth transport. The per-technique CSV
column layout (e.g. the single-crystal goniometer-angle row shape) lives in
the technique's own row builder, not here.
"""

from .control import EICControlModel, SubmittedJob
from .eic_client import EICClient
from .row_builder import EICRowBuilder

__all__ = [
    "EICClient",
    "EICControlModel",
    "EICRowBuilder",
    "SubmittedJob",
]
