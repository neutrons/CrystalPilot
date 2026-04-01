"""Unit tests for src/exphub/agent/ modules.

Covers:
- bridge.py      : snapshot_models, apply_agent_config, _coerce_list_field
- schema_gen.py  : schema_from_model_instance, enrich_schema_with_options
- tools.py       : make_tools factory — set_parameter, set_multiple_parameters,
                   navigate_to_tab
- rag.py         : BeamlineKnowledgeBase indexing and retrieval

No real LLM API calls are made anywhere in this file.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Minimal Pydantic fixtures used by bridge / schema_gen tests
# ---------------------------------------------------------------------------

class _ItemModel(BaseModel):
    phi: float = 0.0
    omega: float = 0.0


class _SubModel(BaseModel):
    ipts_number: str = Field(default="IPTS-0000", title="IPTS Number")
    max_q: float = Field(default=17.0, title="Max Q")
    angle_list_pd: List[_ItemModel] = Field(default_factory=list, title="Angle List")
    crystalsystem: Optional[str] = Field(default=None, title="Crystal System")


class _FakeMainModel(BaseModel):
    """Minimal main model exposing one bridged sub-model."""
    experimentinfo: _SubModel = Field(default_factory=_SubModel)


# patch BRIDGED_SUBMODELS to only include "experimentinfo" for these tests
_FAKE_BRIDGED = ("experimentinfo",)


# ---------------------------------------------------------------------------
# bridge.py
# ---------------------------------------------------------------------------

class TestSnapshotModels:
    def test_returns_flat_dict(self, monkeypatch):
        from exphub.agent import bridge
        monkeypatch.setattr(bridge, "BRIDGED_SUBMODELS", _FAKE_BRIDGED)

        model = _FakeMainModel()
        snap = bridge.snapshot_models(model)

        assert "ipts_number" in snap
        assert snap["ipts_number"] == "IPTS-0000"
        assert "max_q" in snap
        assert snap["max_q"] == 17.0

    def test_list_field_present(self, monkeypatch):
        from exphub.agent import bridge
        monkeypatch.setattr(bridge, "BRIDGED_SUBMODELS", _FAKE_BRIDGED)

        model = _FakeMainModel()
        model.experimentinfo.angle_list_pd = [_ItemModel(phi=10.0, omega=20.0)]
        snap = bridge.snapshot_models(model)

        assert "angle_list_pd" in snap
        assert len(snap["angle_list_pd"]) == 1

    def test_missing_submodel_skipped(self, monkeypatch):
        from exphub.agent import bridge
        monkeypatch.setattr(bridge, "BRIDGED_SUBMODELS", ("nonexistent",))

        model = _FakeMainModel()
        snap = bridge.snapshot_models(model)
        assert snap == {}


class TestApplyAgentConfig:
    def _make_bindings(self):
        bind = MagicMock()
        bind.update_in_view = MagicMock()
        return {"experimentinfo": bind}

    def test_writes_scalar_field(self, monkeypatch):
        from exphub.agent import bridge
        monkeypatch.setattr(bridge, "BRIDGED_SUBMODELS", _FAKE_BRIDGED)

        model = _FakeMainModel()
        bindings = self._make_bindings()
        changed, errors = bridge.apply_agent_config(
            {"ipts_number": "IPTS-1234"}, model, bindings
        )

        assert "ipts_number" in changed
        assert model.experimentinfo.ipts_number == "IPTS-1234"
        assert errors == {}

    def test_no_change_when_value_identical(self, monkeypatch):
        from exphub.agent import bridge
        monkeypatch.setattr(bridge, "BRIDGED_SUBMODELS", _FAKE_BRIDGED)

        model = _FakeMainModel()
        bindings = self._make_bindings()
        changed, errors = bridge.apply_agent_config(
            {"ipts_number": "IPTS-0000"}, model, bindings
        )

        assert changed == []

    def test_returns_error_on_validation_failure(self, monkeypatch):
        from exphub.agent import bridge
        monkeypatch.setattr(bridge, "BRIDGED_SUBMODELS", _FAKE_BRIDGED)

        # Pass a list containing an invalid dict for a List[_ItemModel] field.
        # _coerce_list_field will call _ItemModel(**bad), which raises a
        # Pydantic ValidationError because "phi" expects a float, not a string.
        model = _FakeMainModel()
        bindings = self._make_bindings()
        changed, errors = bridge.apply_agent_config(
            {"angle_list_pd": [{"phi": "not-a-float", "omega": 0.0}]},
            model,
            bindings,
        )

        assert "angle_list_pd" in errors
        assert changed == []

    def test_pushes_binding_when_dirty(self, monkeypatch):
        from exphub.agent import bridge
        monkeypatch.setattr(bridge, "BRIDGED_SUBMODELS", _FAKE_BRIDGED)

        model = _FakeMainModel()
        bindings = self._make_bindings()
        bridge.apply_agent_config({"max_q": 14.0}, model, bindings)

        bindings["experimentinfo"].update_in_view.assert_called_once()


class TestCoerceListField:
    def test_list_of_base_models_from_dicts(self):
        from exphub.agent.bridge import _coerce_list_field

        result = _coerce_list_field(
            _SubModel, "angle_list_pd", [{"phi": 5.0, "omega": 10.0}]
        )
        assert len(result) == 1
        assert isinstance(result[0], _ItemModel)
        assert result[0].phi == 5.0

    def test_plain_list_unchanged(self):
        from exphub.agent.bridge import _coerce_list_field

        result = _coerce_list_field(_SubModel, "max_q", [1, 2, 3])
        assert result == [1, 2, 3]

    def test_non_list_passthrough(self):
        from exphub.agent.bridge import _coerce_list_field

        result = _coerce_list_field(_SubModel, "ipts_number", "IPTS-9999")
        assert result == "IPTS-9999"


# ---------------------------------------------------------------------------
# schema_gen.py
# ---------------------------------------------------------------------------

class TestSchemaFromModelInstance:
    def test_returns_dict(self):
        from exphub.agent.schema_gen import schema_from_model_instance

        props = schema_from_model_instance(_SubModel())
        assert isinstance(props, dict)

    def test_scalar_fields_present(self):
        from exphub.agent.schema_gen import schema_from_model_instance

        props = schema_from_model_instance(_SubModel())
        assert "ipts_number" in props
        assert "max_q" in props

    def test_field_has_title(self):
        from exphub.agent.schema_gen import schema_from_model_instance

        props = schema_from_model_instance(_SubModel())
        assert props["ipts_number"].get("title") == "IPTS Number"

    def test_field_has_type(self):
        from exphub.agent.schema_gen import schema_from_model_instance

        props = schema_from_model_instance(_SubModel())
        assert props["max_q"].get("type") == "number"


class TestEnrichSchemaWithOptions:
    def test_injects_enum_from_list_suffix(self):
        from exphub.agent.schema_gen import enrich_schema_with_options

        schema = {"crystalsystem": {"title": "Crystal System", "type": "string"}}
        snapshot = {"crystalsystem_list": ["Cubic", "Triclinic", "Hexagonal"]}
        enriched = enrich_schema_with_options(schema, snapshot)

        assert enriched["crystalsystem"]["enum"] == ["Cubic", "Triclinic", "Hexagonal"]

    def test_injects_enum_from_options_suffix(self):
        from exphub.agent.schema_gen import enrich_schema_with_options

        schema = {"instrument": {"title": "Instrument", "type": "string"}}
        snapshot = {"instrument_options": ["TOPAZ", "CORELLI", "MANDI"]}
        enriched = enrich_schema_with_options(schema, snapshot)

        assert enriched["instrument"]["enum"] == ["TOPAZ", "CORELLI", "MANDI"]

    def test_ignores_non_string_lists(self):
        from exphub.agent.schema_gen import enrich_schema_with_options

        schema = {"max_q": {"type": "number"}}
        snapshot = {"max_q_list": [14.0, 17.0]}
        enriched = enrich_schema_with_options(schema, snapshot)

        assert "enum" not in enriched["max_q"]

    def test_does_not_mutate_original(self):
        from exphub.agent.schema_gen import enrich_schema_with_options

        schema = {"crystalsystem": {"type": "string"}}
        snapshot = {"crystalsystem_list": ["Cubic"]}
        enrich_schema_with_options(schema, snapshot)

        assert "enum" not in schema["crystalsystem"]


# ---------------------------------------------------------------------------
# tools.py  (make_tools factory)
# ---------------------------------------------------------------------------

def _make_schema():
    return {
        "ipts_number": {"title": "IPTS Number", "type": "string"},
        "max_q": {"title": "Max Q", "type": "number"},
        "instrument": {
            "title": "Instrument",
            "type": "string",
            "enum": ["TOPAZ", "CORELLI", "MANDI"],
        },
    }


class TestSetParameter:
    def test_returns_name_and_value(self):
        from exphub.agent.tools import make_tools

        tools = {t.name: t for t in make_tools(_make_schema())}
        result = tools["set_parameter"].invoke(
            {"parameter_name": "ipts_number", "parameter_value": "IPTS-5678"}
        )
        assert result["parameter_name"] == "ipts_number"
        assert result["parameter_value"] == "IPTS-5678"


class TestValidateMulti:
    """Tests for the _validate_multi closure via set_multiple_parameters."""

    def _get_tool(self, schema=None):
        from exphub.agent.tools import make_tools

        tools = {t.name: t for t in make_tools(schema or _make_schema())}
        return tools["set_multiple_parameters"]

    def test_accepts_valid_values(self):
        tool = self._get_tool()
        result = tool.invoke({"parameters": {"max_q": 14.0, "ipts_number": "IPTS-1"}})
        assert "max_q" in result["validated"]
        assert result["errors"] == {}

    def test_rejects_unknown_parameter(self):
        tool = self._get_tool()
        result = tool.invoke({"parameters": {"nonexistent_field": 42}})
        assert "nonexistent_field" in result["errors"]

    def test_rejects_invalid_enum_value(self):
        tool = self._get_tool()
        result = tool.invoke({"parameters": {"instrument": "UNKNOWN_BEAM"}})
        assert "instrument" in result["errors"]

    def test_accepts_enum_case_insensitive(self):
        tool = self._get_tool()
        result = tool.invoke({"parameters": {"instrument": "topaz"}})
        assert result["validated"].get("instrument") == "TOPAZ"
        assert "instrument" not in result["errors"]


class TestNavigateToTab:
    def _get_tool(self, nav_fn=None):
        from exphub.agent.tools import make_tools

        tools = {t.name: t for t in make_tools(_make_schema(), nav_fn=nav_fn)}
        return tools["navigate_to_tab"]

    def test_resolves_name_to_number(self):
        calls = []
        tool = self._get_tool(nav_fn=lambda n: calls.append(n))
        result = tool.invoke({"tab_name": "ipts_info"})
        assert result["tab"] == 1
        assert calls == [1]

    def test_resolves_integer_string(self):
        calls = []
        tool = self._get_tool(nav_fn=lambda n: calls.append(n))
        result = tool.invoke({"tab_name": "3"})
        assert result["tab"] == 3

    def test_normalises_spaces_and_dashes(self):
        calls = []
        tool = self._get_tool(nav_fn=lambda n: calls.append(n))
        result = tool.invoke({"tab_name": "live-data-processing"})
        assert result["tab"] == 2

    def test_returns_error_for_unknown_name(self):
        tool = self._get_tool(nav_fn=lambda n: None)
        result = tool.invoke({"tab_name": "does_not_exist"})
        assert "error" in result

    def test_returns_error_when_no_nav_fn(self):
        tool = self._get_tool(nav_fn=None)
        result = tool.invoke({"tab_name": "ipts_info"})
        assert "error" in result


# ---------------------------------------------------------------------------
# rag.py
# ---------------------------------------------------------------------------

class TestBeamlineKnowledgeBase:
    @pytest.fixture()
    def kb_dir(self, tmp_path: Path) -> Path:
        """Create a temp knowledge dir with two small docs."""
        (tmp_path / "guide.md").write_text(
            "## TOPAZ Instrument\n"
            "TOPAZ is a single-crystal neutron diffractometer at ORNL BL-12. "
            "It covers wavelengths 0.4–3.5 Angstroms and Q up to 40 inverse Angstroms.\n\n"
            "## Crystal Systems\n"
            "The seven crystal systems are cubic, tetragonal, orthorhombic, "
            "hexagonal, trigonal, monoclinic, and triclinic. "
            "Each has distinct symmetry constraints on lattice parameters.\n",
            encoding="utf-8",
        )
        (tmp_path / "params.txt").write_text(
            "max_q controls the maximum momentum transfer in inverse Angstroms "
            "used during peak search and integration.\n"
            "tolerance is the HKL indexing tolerance (typical range 0.10–0.15).\n",
            encoding="utf-8",
        )
        return tmp_path

    def test_indexes_documents(self, kb_dir):
        from exphub.agent.rag import BeamlineKnowledgeBase

        kb = BeamlineKnowledgeBase(kb_dir)
        assert kb.document_count > 0

    def test_retrieve_returns_results_for_on_topic_query(self, kb_dir):
        from exphub.agent.rag import BeamlineKnowledgeBase

        kb = BeamlineKnowledgeBase(kb_dir)
        results = kb.retrieve("TOPAZ wavelength range", k=3)
        assert len(results) > 0
        assert any("TOPAZ" in r for r in results)

    def test_retrieve_returns_empty_for_garbage_query(self, kb_dir):
        from exphub.agent.rag import BeamlineKnowledgeBase

        kb = BeamlineKnowledgeBase(kb_dir)
        results = kb.retrieve("xyzzy foobarbaz qwerty12345")
        assert results == []

    def test_retrieve_empty_when_no_documents(self, tmp_path):
        from exphub.agent.rag import BeamlineKnowledgeBase

        kb = BeamlineKnowledgeBase(tmp_path)
        assert kb.retrieve("anything") == []

    def test_heading_aware_chunks_stay_together(self, tmp_path):
        """Verify that section-aware chunking doesn't split a short section."""
        from exphub.agent.rag import _chunk_text

        text = (
            "## TOPAZ\nTOPAZ is a great instrument for neutron diffraction.\n\n"
            "## CORELLI\nCORELLI is used for diffuse scattering experiments.\n"
        )
        chunks = _chunk_text(text, "test.md")
        # Each short section should be its own chunk (not merged or split)
        topaz_chunks = [c for c in chunks if "TOPAZ is a great" in c]
        corelli_chunks = [c for c in chunks if "CORELLI is used" in c]
        assert len(topaz_chunks) >= 1
        assert len(corelli_chunks) >= 1
        # The two sections should be in separate chunks
        assert not any("TOPAZ is a great" in c and "CORELLI is used" in c for c in chunks)


# ---------------------------------------------------------------------------
# validation.py
# ---------------------------------------------------------------------------

class TestValidatePointGroup:
    def test_valid_combination(self):
        from exphub.agent.validation import validate_point_group

        assert validate_point_group("m-3m", "Cubic") is None

    def test_invalid_combination(self):
        from exphub.agent.validation import validate_point_group

        err = validate_point_group("2/m", "Cubic")
        assert err is not None
        assert "not valid" in err

    def test_no_crystal_system(self):
        from exphub.agent.validation import validate_point_group

        assert validate_point_group("m-3m", None) is None


class TestValidateCentering:
    def test_valid_combination(self):
        from exphub.agent.validation import validate_centering

        assert validate_centering("P", "1") is None

    def test_invalid_combination(self):
        from exphub.agent.validation import validate_centering

        err = validate_centering("F", "1")
        assert err is not None
        assert "not valid" in err

    def test_no_point_group(self):
        from exphub.agent.validation import validate_centering

        assert validate_centering("P", None) is None


class TestDependentFieldsToReset:
    def test_crystal_system_resets_both(self):
        from exphub.agent.validation import dependent_fields_to_reset

        assert dependent_fields_to_reset("crystalsystem") == ["point_group", "centering"]

    def test_point_group_resets_centering(self):
        from exphub.agent.validation import dependent_fields_to_reset

        assert dependent_fields_to_reset("point_group") == ["centering"]

    def test_unrelated_field_resets_nothing(self):
        from exphub.agent.validation import dependent_fields_to_reset

        assert dependent_fields_to_reset("molecular_formula") == []


class TestCheckUnitCellVolume:
    def test_reasonable_volume_passes(self):
        from exphub.agent.validation import check_unit_cell_volume

        cfg = {"molecular_formula": "NaCl", "Z": 4, "unit_cell_volume": 180.0}
        is_err, msg = check_unit_cell_volume(cfg)
        assert not is_err

    def test_too_small_volume_fails(self):
        from exphub.agent.validation import check_unit_cell_volume

        # NaCl has 2 atoms, Z=4 → threshold = 2*4*10 = 80
        cfg = {"molecular_formula": "NaCl", "Z": 4, "unit_cell_volume": 10.0}
        is_err, msg = check_unit_cell_volume(cfg)
        assert is_err
        assert "small" in msg

    def test_missing_fields_passes(self):
        from exphub.agent.validation import check_unit_cell_volume

        cfg = {"molecular_formula": "NaCl"}
        is_err, msg = check_unit_cell_volume(cfg)
        assert not is_err

    def test_zero_z_fails(self):
        from exphub.agent.validation import check_unit_cell_volume

        cfg = {"molecular_formula": "NaCl", "Z": 0, "unit_cell_volume": 180.0}
        is_err, msg = check_unit_cell_volume(cfg)
        assert is_err
        assert "Z must be" in msg

    def test_complex_formula(self):
        from exphub.agent.validation import check_unit_cell_volume

        # C6H12O6 = 24 atoms, Z=2 → threshold = 24*2*10 = 480
        cfg = {"molecular_formula": "C6H12O6", "Z": 2, "unit_cell_volume": 500.0}
        is_err, msg = check_unit_cell_volume(cfg)
        assert not is_err
