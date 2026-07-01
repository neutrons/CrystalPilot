"""Parser for ReduceSCD-style reduction ``.config`` files (pure, no Mantid).

The TOPAZ ReductionGUI writes ``ReduceSCD.config`` files consumed by
``ReduceSCD_Parallel.py`` via Mantid's ``ReduceDictionary``. The format is
line-oriented: ``#`` starts a comment, blank lines are ignored, and each
remaining line is ``key<whitespace>value...`` (the value is the remainder of
the line). Only reads are performed here.
"""

from __future__ import annotations

from typing import Dict, List

from .models import ReductionConfig
from .safety import safe_open


def parse_config_text(text: str, source_path: str = "<memory>") -> ReductionConfig:
    """Parse the text of a ReduceSCD ``.config`` into a :class:`ReductionConfig`."""
    values: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        key = parts[0].strip()
        value = parts[1].strip() if len(parts) > 1 else ""
        values[key] = value
    run_numbers = expand_run_numbers(values.get("run_nums", ""))
    return ReductionConfig(source_path=source_path, values=values, run_numbers=run_numbers)


def parse_config_file(path: str) -> ReductionConfig:
    """Read and parse a ReduceSCD ``.config`` file from disk (read-only)."""
    with safe_open(path, "r") as handle:
        text = handle.read()
    return parse_config_text(str(text), source_path=path)


def expand_run_numbers(spec: str) -> List[int]:
    """Expand a run spec like ``"12,15,20:23"`` into ``[12,15,20,21,22,23]``.

    Supports comma-separated tokens; a token may be a single integer or an
    inclusive range using ``:`` or ``-`` as the separator. Unparseable tokens
    are skipped rather than raising, so a malformed field never aborts a batch.
    """
    runs: List[int] = []
    if not spec or spec.strip().lower() == "none":
        return runs
    for token in spec.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        sep = ":" if ":" in token else ("-" if "-" in token.lstrip("-") else "")
        try:
            if sep and sep in token.lstrip("-"):
                lo_str, hi_str = token.split(sep, 1)
                lo, hi = int(lo_str), int(hi_str)
                if lo <= hi:
                    runs.extend(range(lo, hi + 1))
            else:
                runs.append(int(token))
        except ValueError:
            continue
    return runs
