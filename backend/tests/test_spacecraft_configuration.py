from fastapi.testclient import TestClient

from app.main import app
from app.missions.project_routes import get_mission_project_store
from app.missions.projects import MissionProjectDraft
from app.missions.spacecraft import SpacecraftConfigurationDraft
from app.missions.spacecraft_routes import get_spacecraft_configuration_store
from app.storage.mission_projects import MissionProjectStore
from app.storage.spacecraft_configurations import SpacecraftConfigurationStore

client = TestClient(app)


def project_payload() -> dict:
    return {
        "name": "Orbiter mission concept",
        "summary": "A preliminary science orbiter project.",
        "target_body": "Mars",
        "mission_archetype": "orbiter",
        "primary_objective": "Characterize a selected planetary environment using a remote sensing payload.",
        "intended_users": ["engineering team"],
        "requirements": [],
    }


def engineering_value(value_id: str, name: str, value: float, unit: str, dimension: str) -> dict:
    return {
        "value_id": value_id,
        "name": name,
        "value": value,
        "unit": unit,
        "dimension": dimension,
        "provenance": "illustrative",
        "assumption_note": "Test fixture value only; not a hardware specification.",
        "intended_use": "Exercise spacecraft budget arithmetic in automated tests.",
        "credibility": "unvalidated",
        "limitations": ["Not sourced or validated."],
    }


def spacecraft_payload(mass: float = 12.0) -> dict:
    return {
        "name": "Reference bus",
        "description": "Illustrative component configuration for API tests.",
        "mass_margin_percent": 20.0,
        "assumptions": ["All test values are illustrative."],
        "components": [
            {
                "component_id": "EPS-001",
                "name": "Power subsystem",
                "subsystem": "power",
                "mass": engineering_value("mass-eps", "EPS mass", mass, "kg", "mass"),
                "power_draw": engineering_value("draw-eps", "EPS load", 30.0, "W", "power"),
                "power_generation": engineering_value("gen-eps", "EPS generation", 80.0, "W", "power"),
                "load_duty_cycle": 0.5,
                "generation_duty_cycle": 0.8,
            },
            {
                "component_id": "COM-001",
                "name": "Communications unit",
                "subsystem": "communications",
                "mass": engineering_value("mass-com", "Communications mass", 8.0, "kg", "mass"),
                "power_draw": engineering_value("draw-com", "Communications load", 20.0, "W", "power"),
                "load_duty_cycle": 0.25,
                "generation_duty_cycle": 0.0,
            },
        ],
    }


def test_configuration_and_budgets_are_saved_and_calculated(tmp_path) -> None:
    database = tmp_path / "spacecraft.sqlite3"
    projects = MissionProjectStore(database)
    spacecraft = SpacecraftConfigurationStore(database)
    app.dependency_overrides[get_mission_project_store] = lambda: projects
    app.dependency_overrides[get_spacecraft_configuration_store] = lambda: spacecraft
    try:
        project = projects.create(MissionProjectDraft.model_validate(project_payload()))
        created = client.post(
            f"/api/v1/missions/projects/{project.project_id}/spacecraft/configuration",
            json=spacecraft_payload(),
        )
        assert created.status_code == 201
        assert created.json()["latest_revision"] == 1

        budgets = client.get(f"/api/v1/missions/projects/{project.project_id}/spacecraft/budgets")
        assert budgets.status_code == 200
        assert budgets.json()["mass"]["component_mass_kg"] == 20.0
        assert budgets.json()["mass"]["margin_mass_kg"] == 4.0
        assert budgets.json()["mass"]["total_with_margin_kg"] == 24.0
        assert budgets.json()["power"]["average_generation_w"] == 64.0
        assert budgets.json()["power"]["average_load_w"] == 20.0
        assert budgets.json()["power"]["net_power_w"] == 44.0
    finally:
        app.dependency_overrides.pop(get_mission_project_store, None)
        app.dependency_overrides.pop(get_spacecraft_configuration_store, None)


def test_configuration_revision_is_append_only(tmp_path) -> None:
    database = tmp_path / "spacecraft.sqlite3"
    projects = MissionProjectStore(database)
    store = SpacecraftConfigurationStore(database)
    project = projects.create(MissionProjectDraft.model_validate(project_payload()))
    store.create(project.project_id, SpacecraftConfigurationDraft.model_validate(spacecraft_payload()))
    revised = store.create_revision(
        project.project_id,
        SpacecraftConfigurationDraft.model_validate(spacecraft_payload(15.0)),
    )
    assert revised.latest_revision == 2
    with store._connection() as connection:
        rows = connection.execute(
            "SELECT revision_number FROM spacecraft_configuration_revisions ORDER BY revision_number"
        ).fetchall()
    assert [row["revision_number"] for row in rows] == [1, 2]


def test_component_rejects_mass_with_wrong_dimension() -> None:
    payload = spacecraft_payload()
    payload["components"][0]["mass"] = engineering_value(
        "bad-mass", "Bad mass", 12.0, "W", "power"
    )
    response = client.post(
        "/api/v1/missions/projects/00000000-0000-0000-0000-000000000000/spacecraft/configuration",
        json=payload,
    )
    assert response.status_code == 422


def test_duplicate_component_ids_are_rejected() -> None:
    payload = spacecraft_payload()
    payload["components"][1]["component_id"] = payload["components"][0]["component_id"]
    response = client.post(
        "/api/v1/missions/projects/00000000-0000-0000-0000-000000000000/spacecraft/configuration",
        json=payload,
    )
    assert response.status_code == 422


def test_unknown_project_returns_404(tmp_path) -> None:
    store = SpacecraftConfigurationStore(tmp_path / "spacecraft.sqlite3")
    app.dependency_overrides[get_spacecraft_configuration_store] = lambda: store
    try:
        response = client.get(
            "/api/v1/missions/projects/00000000-0000-0000-0000-000000000000/spacecraft/configuration"
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_spacecraft_configuration_store, None)
