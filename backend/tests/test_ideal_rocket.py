from math import log

import pytest
from pydantic import ValidationError

from app.propulsion.ideal_rocket import (
    STANDARD_GRAVITY,
    IdealRocketEquationRequest,
    calculate_ideal_delta_v,
)


def input_value(
    value_id: str,
    name: str,
    value: float,
    unit: str,
    dimension: str,
) -> dict:
    return {
        "value_id": value_id,
        "name": name,
        "value": value,
        "unit": unit,
        "dimension": dimension,
        "provenance": "illustrative",
        "assumption_note": "Synthetic test input; not a vehicle specification.",
        "intended_use": "Unit test of the ideal rocket equation implementation.",
        "credibility": "unvalidated",
    }


def valid_request() -> dict:
    return {
        "dry_mass": input_value("dry.mass", "Dry mass", 1000, "kg", "mass"),
        "propellant_mass": input_value("propellant.mass", "Propellant mass", 1000, "kg", "mass"),
        "specific_impulse": input_value("engine.isp", "Specific impulse", 300, "s", "time"),
        "intended_use": "Verify the ideal equation implementation with synthetic values.",
    }


def test_ideal_rocket_equation_matches_reference_calculation() -> None:
    request = IdealRocketEquationRequest.model_validate(valid_request())

    result = calculate_ideal_delta_v(request)

    assert result.delta_v.value == pytest.approx(2039.2355394714561, rel=1e-12)
    assert result.delta_v.value == pytest.approx(300 * 9.80665 * log(2))
    assert result.initial_mass.value == 2000
    assert result.mass_ratio.value == 2
    assert result.delta_v.unit == "m/s"
    assert result.delta_v.provenance == "calculated"
    assert result.delta_v.credibility == "unvalidated"
    assert result.equation_id == "PROPULSION.IDEAL_ROCKET_EQUATION.V1"
    assert len(result.input_values) == 3


def test_standard_gravity_is_traceable_and_not_lunar_gravity() -> None:
    assert STANDARD_GRAVITY.value == 9.80665
    assert STANDARD_GRAVITY.source is not None
    assert "not lunar surface gravity" in STANDARD_GRAVITY.intended_use


def test_ideal_rocket_equation_rejects_wrong_mass_units() -> None:
    payload = valid_request()
    payload["dry_mass"] = input_value("dry.mass", "Dry mass", 1000, "m", "length")

    with pytest.raises(ValidationError):
        IdealRocketEquationRequest.model_validate(payload)


def test_ideal_rocket_equation_rejects_zero_propellant() -> None:
    payload = valid_request()
    payload["propellant_mass"]["value"] = 0

    with pytest.raises(ValidationError):
        IdealRocketEquationRequest.model_validate(payload)


def test_ideal_rocket_equation_rejects_duplicate_input_ids() -> None:
    payload = valid_request()
    payload["propellant_mass"]["value_id"] = "dry.mass"

    with pytest.raises(ValidationError):
        IdealRocketEquationRequest.model_validate(payload)


def test_ideal_rocket_equation_api_marks_result_unvalidated() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.post("/api/v1/models/propulsion/ideal-delta-v", json=valid_request())

    assert response.status_code == 200
    assert response.json()["delta_v"]["credibility"] == "unvalidated"
    assert response.json()["limitations"]
