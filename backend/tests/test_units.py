from app.engineering.provenance import EngineeringValue
from app.engineering.units import Dimension, unit_dimension
from pydantic import ValidationError


def sample() -> dict:
    return {
        "value_id": "fixture.velocity",
        "name": "Fixture velocity",
        "value": 1.2,
        "unit": "m/s",
        "dimension": "velocity",
        "provenance": "illustrative",
        "assumption_note": "Synthetic test fixture only.",
        "intended_use": "Unit-contract test.",
    }


def test_unit_registry_maps_known_units() -> None:
    assert unit_dimension("m/s") == Dimension.VELOCITY
    assert unit_dimension("Wh") == Dimension.ENERGY
    assert unit_dimension("unknown-unit") is None


def test_quantity_rejects_dimension_mismatch() -> None:
    payload = sample()
    payload["dimension"] = "mass"
    try:
        EngineeringValue.model_validate(payload)
    except ValidationError:
        pass
    else:
        raise AssertionError("Dimension mismatch must be rejected")


def test_quantity_rejects_unknown_unit() -> None:
    payload = sample()
    payload["unit"] = "parsec-ish"
    try:
        EngineeringValue.model_validate(payload)
    except ValidationError:
        pass
    else:
        raise AssertionError("Unknown unit must be rejected")


def test_quantity_accepts_matching_unit_and_dimension() -> None:
    parsed = EngineeringValue.model_validate(sample())
    assert parsed.dimension == Dimension.VELOCITY
