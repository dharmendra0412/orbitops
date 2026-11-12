from fastapi.testclient import TestClient

from app.main import app
from app.missions.catalog import PlanetId, get_mission_catalog


def test_catalog_contains_all_eight_planets() -> None:
    catalog = get_mission_catalog()

    assert len(catalog.destinations) == 8
    assert {destination.planet_id for destination in catalog.destinations} == set(PlanetId)
    assert all(destination.feasibility_status == "not_assessed" for destination in catalog.destinations)


def test_catalog_exposes_multiple_mission_archetypes() -> None:
    catalog = get_mission_catalog()

    assert {item.archetype.value for item in catalog.mission_archetypes} == {
        "flyby", "orbiter", "atmospheric_probe", "entry_descent_landing",
        "lander", "rover", "sample_return",
    }


def test_mission_catalog_api_does_not_claim_feasibility() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/missions/catalog")

    assert response.status_code == 200
    assert response.json()["scope"] == "eight_planets"
    assert "Mission-archetype compatibility and physical feasibility have not been assessed." in response.json()["exclusions"]
