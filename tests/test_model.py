"""Test package for model classes."""

from exphub.techniques.single_crystal.models.root import SingleCrystalMainModel


def test_main_model_defaults() -> None:
    model = SingleCrystalMainModel()
    assert model.username == "test_name"
    assert model.password == "test_password"
