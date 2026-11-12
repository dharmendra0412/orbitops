from math import isclose

import pytest
from pydantic import ValidationError

from app.power.energy_balance import (
    SimpleEnergyBalanceRequest,
    calculate_simple_energy_balance,
)


def input_value(value_id: str, name: str, value: float, unit: str, dimension: str) -> dict:
    return {
        "value_id": value_id,
        "name": name,
        "value": value,
        "unit": unit,
        "dimension": dimension,
        "provenance": "illustrative",
        "assumption_note": "Synthetic test input; not a lander subsystem specification.",
        "intended_use": "Unit test of constant-power energy balance.",
        "credibility": "unvalidated",
    }


def valid_request() -> dict:
    return {
        "supply_power": input_value("power.supply", "Average supply power", 150, "W", "power"),
        "load_power": input_value("power.load", "Average load power", 100, "W", "power"),
        "duration": input_value("duration.interval", "Interval duration", 10, "h", "time"),
        "intended_use": "Test energy balance with synthetic values.",
    }


def test_simple_energy_balance_calculates_energy_and_margin() -> None:
    request = SimpleEnergyBalanceRequest.model_validate(valid_request())

    result = calculate_simple_energy_balance(request)

    assert result.supply_energy.value == 1500
    assert result.load_energy.value == 1000
    assert result.energy_margin.value == 500
    assert result.margin_fraction.value == 0.5
    assert result.energy_margin.credibility == "unvalidated"


def test_simple_energy_balance_allows_negative_energy_margin() -> None:
    payload = valid_request()
    payload["supply_power"]["value"] = 50

    result = calculate_simple_energy_balance(SimpleEnergyBalanceRequest.model_validate(payload))

    assert result.energy_margin.value == -500


def test_simple_energy_balance_rejects_wrong_units() -> None:
    payload = valid_request()
    payload["duration"] = input_value("duration.interval", "Interval duration", 10, "s", "time")

    with pytest.raises(ValidationError):
        SimpleEnergyBalanceRequest.model_validate(payload)


def test_simple_energy_balance_rejects_negative_supply_power() -> None:
    payload = valid_request()
    payload["supply_power"]["value"] = -1

    with pytest.raises(ValidationError):
        SimpleEnergyBalanceRequest.model_validate(payload)


def test_simple_energy_balance_rejects_duplicate_input_ids() -> None:
    payload = valid_request()
    payload["load_power"]["value_id"] = "power.supply"

    with pytest.raises(ValidationError):
        SimpleEnergyBalanceRequest.model_validate(payload)


def test_simple_energy_balance_outputs_finite_margin_fraction() -> None:
    result = calculate_simple_energy_balance(
        SimpleEnergyBalanceRequest.model_validate(valid_request())
    )

    assert isclose(result.margin_fraction.value, 0.5)
    assert result.margin_fraction.unit == "1"



def test_simple_energy_balance_api_marks_output_unvalidated() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.post("/api/v1/models/power/simple-energy-balance", json=valid_request())

    assert response.status_code == 200
    assert response.json()["energy_margin"]["credibility"] == "unvalidated"
    assert response.json()["limitations"]
