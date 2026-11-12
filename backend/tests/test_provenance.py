import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.engineering.provenance import EngineeringValue
from app.main import app

client = TestClient(app)


def base_payload() -> dict:
    return {
        "value_id": "test.mass.001",
        "name": "Test mass",
        "value": 12.5,
        "unit": "kg",
        "provenance": "illustrative",
        "assumption_note": "Synthetic test fixture; not a spacecraft specification.",
        "intended_use": "Exercise the provenance contract only.",
        "credibility": "unvalidated",
    }


def test_illustrative_value_requires_assumption_note() -> None:
    payload = base_payload()
    payload.pop("assumption_note")
    with pytest.raises(ValidationError):
        EngineeringValue.model_validate(payload)


def test_sourced_value_requires_source_reference() -> None:
    payload = base_payload()
    payload["provenance"] = "sourced"
    payload.pop("assumption_note")
    with pytest.raises(ValidationError):
        EngineeringValue.model_validate(payload)


def test_calculated_value_requires_equation_and_model_version() -> None:
    payload = base_payload()
    payload["provenance"] = "calculated"
    payload.pop("assumption_note")
    with pytest.raises(ValidationError):
        EngineeringValue.model_validate(payload)


def test_non_finite_values_are_rejected() -> None:
    payload = base_payload()
    payload["value"] = float("nan")
    with pytest.raises(ValidationError):
        EngineeringValue.model_validate(payload)


def test_valid_illustrative_contract_is_accepted_by_api() -> None:
    response = client.post("/api/v1/engineering/values/validate", json=base_payload())
    assert response.status_code == 200
    assert response.json()["provenance"] == "illustrative"
    assert response.json()["credibility"] == "unvalidated"


def test_validated_claim_requires_limitations() -> None:
    payload = base_payload()
    payload["credibility"] = "validated"
    with pytest.raises(ValidationError):
        EngineeringValue.model_validate(payload)
