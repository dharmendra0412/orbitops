import math

from fastapi.testclient import TestClient

from app.main import app
from app.orbital.routes import get_orbital_model_run_store
from app.storage.model_runs import ModelRunStore

client = TestClient(app)

MU = 3.986004418e14
RADIUS = 7_000_000.0


def quantity(value_id: str, name: str, value: float, unit: str, dimension: str) -> dict:
    return {
        "value_id": value_id,
        "name": name,
        "value": value,
        "unit": unit,
        "dimension": dimension,
        "provenance": "illustrative",
        "assumption_note": "Synthetic orbital mechanics test input.",
        "intended_use": "Automated analytical model tests only.",
        "credibility": "unvalidated",
        "limitations": ["Not a flight dynamics input."],
    }


def mu_input() -> dict:
    return quantity("mu-earth-test", "Central-body gravitational parameter", MU, "m^3/s^2", "gravitational_parameter")


def radius_input(value_id: str, name: str, value: float) -> dict:
    return quantity(value_id, name, value, "m", "length")


def configured_store(tmp_path):
    store = ModelRunStore(tmp_path / "orbital-runs.sqlite3")
    app.dependency_overrides[get_orbital_model_run_store] = lambda: store
    return store


def clear_overrides() -> None:
    app.dependency_overrides.pop(get_orbital_model_run_store, None)


def test_circular_orbit_velocity_matches_two_body_formula(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        response = client.post(
            "/api/v1/models/orbital-mechanics/circular-orbit",
            json={
                "gravitational_parameter": mu_input(),
                "orbital_radius": radius_input("r-circular", "Orbit radius", RADIUS),
                "intended_use": "Preliminary circular-orbit velocity estimate.",
            },
        )
        assert response.status_code == 200
        assert math.isclose(response.json()["output"]["value"], math.sqrt(MU / RADIUS), rel_tol=1e-12)
        assert response.json()["output"]["credibility"] == "unvalidated"
        assert response.json()["run_id"]
    finally:
        clear_overrides()


def test_vis_viva_reduces_to_circular_velocity_when_radius_equals_semimajor_axis(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        response = client.post(
            "/api/v1/models/orbital-mechanics/vis-viva",
            json={
                "gravitational_parameter": mu_input(),
                "orbital_radius": radius_input("r-vis", "Current radius", RADIUS),
                "semi_major_axis": radius_input("a-vis", "Semi-major axis", RADIUS),
                "intended_use": "Check the circular-orbit limit of the vis-viva equation.",
            },
        )
        assert response.status_code == 200
        assert math.isclose(response.json()["output"]["value"], math.sqrt(MU / RADIUS), rel_tol=1e-12)
    finally:
        clear_overrides()


def test_keplerian_period_and_escape_velocity(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        period = client.post(
            "/api/v1/models/orbital-mechanics/orbital-period",
            json={
                "gravitational_parameter": mu_input(),
                "semi_major_axis": radius_input("a-period", "Semi-major axis", RADIUS),
                "intended_use": "Preliminary Keplerian orbital period estimate.",
            },
        )
        escape = client.post(
            "/api/v1/models/orbital-mechanics/escape-velocity",
            json={
                "gravitational_parameter": mu_input(),
                "orbital_radius": radius_input("r-escape", "Escape radius", RADIUS),
                "intended_use": "Preliminary local two-body escape velocity estimate.",
            },
        )
        assert period.status_code == 200
        assert escape.status_code == 200
        assert math.isclose(
            period.json()["output"]["value"],
            2.0 * math.pi * math.sqrt(RADIUS**3 / MU),
            rel_tol=1e-12,
        )
        circular = math.sqrt(MU / RADIUS)
        assert math.isclose(escape.json()["output"]["value"], math.sqrt(2.0) * circular, rel_tol=1e-12)
    finally:
        clear_overrides()


def test_hohmann_transfer_produces_positive_burns_and_transfer_time(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        response = client.post(
            "/api/v1/models/orbital-mechanics/hohmann-transfer",
            json={
                "gravitational_parameter": mu_input(),
                "initial_orbit_radius": radius_input("r1-hohmann", "Initial orbit radius", RADIUS),
                "target_orbit_radius": radius_input("r2-hohmann", "Target orbit radius", 14_000_000.0),
                "intended_use": "Preliminary coplanar circular-orbit Hohmann transfer estimate.",
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["transfer_delta_v"]["value"] > 0
        assert result["first_burn_delta_v"]["value"] > 0
        assert result["second_burn_delta_v"]["value"] > 0
        assert math.isclose(
            result["transfer_delta_v"]["value"],
            result["first_burn_delta_v"]["value"] + result["second_burn_delta_v"]["value"],
            rel_tol=1e-12,
        )
        assert result["transfer_time"]["value"] > 0
        assert result["run_id"]
        assert "ephemerides" in " ".join(result["limitations"])
    finally:
        clear_overrides()


def test_orbital_mechanics_rejects_wrong_gravitational_parameter_dimension(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        bad_mu = quantity("mu-bad", "Invalid mu", 1.0, "kg", "mass")
        response = client.post(
            "/api/v1/models/orbital-mechanics/circular-orbit",
            json={
                "gravitational_parameter": bad_mu,
                "orbital_radius": radius_input("r-bad-mu", "Orbit radius", RADIUS),
                "intended_use": "Test invalid dimensional input.",
            },
        )
        assert response.status_code == 422
    finally:
        clear_overrides()


def test_hohmann_transfer_rejects_equal_orbit_radii(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        response = client.post(
            "/api/v1/models/orbital-mechanics/hohmann-transfer",
            json={
                "gravitational_parameter": mu_input(),
                "initial_orbit_radius": radius_input("r1-equal", "Initial radius", RADIUS),
                "target_orbit_radius": radius_input("r2-equal", "Target radius", RADIUS),
                "intended_use": "Test equal-orbit rejection.",
            },
        )
        assert response.status_code == 422
    finally:
        clear_overrides()


def test_vis_viva_rejects_non_real_bound_orbit_input(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        response = client.post(
            "/api/v1/models/orbital-mechanics/vis-viva",
            json={
                "gravitational_parameter": mu_input(),
                "orbital_radius": radius_input("r-vis-invalid", "Current radius", RADIUS),
                "semi_major_axis": radius_input("a-vis-invalid", "Semi-major axis", 1_000_000.0),
                "intended_use": "Test vis-viva domain validation.",
            },
        )
        assert response.status_code == 422
    finally:
        clear_overrides()
