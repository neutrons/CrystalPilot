"""Tests for the discovery phase (filesystem + config mapping) with a fake reader."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict

from scripts.cp_bench.discover import (
    MetadataReader,
    config_for_run,
    discover_ipts,
    find_nexus_files,
    find_reduction_configs,
)
from scripts.cp_bench.models import RunInfo

ReaderFactory = Callable[[Dict[int, RunInfo]], MetadataReader]


def _make_tree(tmp_path: Path) -> tuple[str, str]:
    nexus = tmp_path / "nexus"
    nexus.mkdir()
    (nexus / "TOPAZ_100.nxs.h5").write_text("")
    (nexus / "TOPAZ_102.nxs.h5").write_text("")
    (nexus / "TOPAZ_105.nxs").write_text("")  # legacy extension
    (nexus / "notes.txt").write_text("")  # ignored

    shared = tmp_path / "shared"
    gui = shared / "ReductionGUI"
    gui.mkdir(parents=True)
    (gui / "reduce.config").write_text("instrument_name TOPAZ\nrun_nums 100,102\ncell_type Monoclinic\n")
    (shared / "other.config").write_text("instrument_name TOPAZ\nrun_nums 105\n")
    return str(nexus), str(shared)


def test_find_nexus_files(tmp_path: Path) -> None:
    nexus_dir, _ = _make_tree(tmp_path)
    found = find_nexus_files(nexus_dir)
    assert set(found) == {100, 102, 105}
    assert found[100].endswith("TOPAZ_100.nxs.h5")


def test_find_reduction_configs_prioritises_gui(tmp_path: Path) -> None:
    _, shared_dir = _make_tree(tmp_path)
    configs = find_reduction_configs(shared_dir)
    assert len(configs) == 2
    # ReductionGUI config sorts first.
    assert "ReductionGUI" in configs[0].source_path


def test_config_for_run_membership(tmp_path: Path) -> None:
    _, shared_dir = _make_tree(tmp_path)
    configs = find_reduction_configs(shared_dir)
    assert config_for_run(100, configs) is not None
    assert config_for_run(105, configs) is not None
    assert config_for_run(999, configs) is None


def test_discover_ipts_maps_runs(tmp_path: Path, fake_reader_factory: ReaderFactory) -> None:
    nexus_dir, shared_dir = _make_tree(tmp_path)
    runs: Dict[int, RunInfo] = {
        100: RunInfo(run_number=100, nxs_path="", duration_s=1000.0, total_proton_charge=5.0),
    }
    reader = fake_reader_factory(runs)
    manifest = discover_ipts(1, nexus_dir, shared_dir, reader)
    assert manifest.ipts == 1
    assert {r.run_number for r in manifest.runs} == {100, 102, 105}
    assert manifest.run_config_map[100].endswith(".config")
    assert manifest.run_config_map[105].endswith("other.config")
    # Serialisation is JSON-ready.
    assert manifest.to_dict()["ipts"] == 1
