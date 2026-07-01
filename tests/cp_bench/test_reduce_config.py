"""Tests for the ReduceSCD .config parser."""

from __future__ import annotations

from scripts.cp_bench.reduce_config import expand_run_numbers, parse_config_text

_SAMPLE = """
# TOPAZ reduction config
instrument_name  TOPAZ
calibration_file_1  /SNS/TOPAZ/shared/cal/2026A.DetCal
run_nums  100,102,105:107
cell_type  Monoclinic
centering  P
min_d  3.0
max_d  25.0
tolerance  0.12
read_UB  True
UB_filename  None
"""


def test_parse_basic_keys() -> None:
    cfg = parse_config_text(_SAMPLE, source_path="mem")
    assert cfg.get("instrument_name") == "TOPAZ"
    assert cfg.get("calibration_file_1").endswith("2026A.DetCal")
    assert cfg.get("cell_type") == "Monoclinic"


def test_typed_accessors() -> None:
    cfg = parse_config_text(_SAMPLE)
    assert cfg.get_float("min_d", 0.0) == 3.0
    assert cfg.get_int("run_nums_missing", 7) == 7
    assert cfg.get_float("tolerance", 1.0) == 0.12
    # "None" is treated as unset.
    assert cfg.get_optional("UB_filename") is None
    assert cfg.get_optional("cell_type") == "Monoclinic"


def test_run_number_expansion() -> None:
    cfg = parse_config_text(_SAMPLE)
    assert cfg.run_numbers == [100, 102, 105, 106, 107]


def test_expand_run_numbers_variants() -> None:
    assert expand_run_numbers("12") == [12]
    assert expand_run_numbers("12,14") == [12, 14]
    assert expand_run_numbers("20:22") == [20, 21, 22]
    assert expand_run_numbers("20-22") == [20, 21, 22]
    assert expand_run_numbers("") == []
    assert expand_run_numbers("None") == []
    # Malformed tokens are skipped, not fatal.
    assert expand_run_numbers("5,abc,7") == [5, 7]


def test_comments_and_blank_lines_ignored() -> None:
    cfg = parse_config_text("# only a comment\n\n   \n")
    assert cfg.values == {}
    assert cfg.run_numbers == []
