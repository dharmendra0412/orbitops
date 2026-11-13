from fastapi.testclient import TestClient

from app.main import app
from app.missions.projects import MissionProjectDraft
from app.missions.spacecraft import SpacecraftConfigurationDraft
from app.storage.mission_projects import MissionProjectStore
from app.storage.requirement_traceability import RequirementTraceabilityStore
from app.storage.revision_impact import RevisionImpactStore
from app.storage.spacecraft_configurations import SpacecraftConfigurationStore
from app.missions.revision_impact_routes import get_revision_impact_store
from app.missions.traceability_routes import get_requirement_traceability_store
from app.missions.traceability import RequirementAllocationCreate

client = TestClient(app)


def mission_payload() -> dict:
    return {
        "name": "Revision impact mission",
        "summary": "Mission fixture for revision comparison.",
        "target_body": "Mars",
        "mission_archetype": "orbiter",
        "primary_objective": "Acquire science observations and return them to the ground segment.",
        "requirements": [
            {
                "requirement_id": "SCI-001",
                "title": "Acquire images",
                "statement": "The payload shall acquire target images.",
                "category": "science",
                "verification_method": "test",
                "acceptance_criteria": "A test demonstrates image acquisition.",
            },
            {
                "requirement_id": "COM-001",
                "title": "Transmit data",
                "statement": "The spacecraft shall transmit science data.",
                "category": "communications",
                "verification_method": "analysis",
                "acceptance_criteria": "Analysis demonstrates data return.",
            },
        ],
    }


def quantity(value_id: str, name: str, value: float, unit: str, dimension: str) -> dict:
    return {
        "value_id": value_id,
        "name": name,
        "value": value,
        "unit": unit,
        "dimension": dimension,
        "provenance": "illustrative",
        "assumption_note": "Synthetic test fixture only.",
        "intended_use": "Revision impact automated tests.",
        "credibility": "unvalidated",
        "limitations": ["Not a real spacecraft specification."],
    }


def spacecraft_payload(component_ids: list[str] | None = None, payload_mass: float = 4.0) -> dict:
    ids = component_ids or ["PAY-001", "COM-001"]
    components = []
    for component_id in ids:
        components.append({
            "component_id": component_id,
            "name": component_id + " unit",
            "subsystem": "payload" if component_id.startswith("PAY") else "communications",
            "mass": quantity("mass-" + component_id, "Component mass", payload_mass if component_id.startswith("PAY") else 3.0, "kg", "mass"),
            "load_duty_cycle": 1.0,
            "generation_duty_cycle": 0.0,
        })
    return {
        "name": "Revision impact spacecraft",
        "description": "Synthetic configuration fixture.",
        "mass_margin_percent": 10.0,
        "assumptions": ["Synthetic test values."],
        "components": components,
    }


def setup_project(tmp_path):
    database = tmp_path / "revision-impact.sqlite3"
    projects = MissionProjectStore(database)
    spacecraft = SpacecraftConfigurationStore(database)
    traceability = RequirementTraceabilityStore(database)
    project = projects.create(MissionProjectDraft.model_validate(mission_payload()))
    spacecraft.create(project.project_id, SpacecraftConfigurationDraft.model_validate(spacecraft_payload()))
    traceability.create(
        project.project_id,
        RequirementAllocationCreate(
            requirement_id="SCI-001",
            component_id="PAY-001",
            rationale="Payload component owns the image acquisition function.",
            allocated_by="Test systems engineer",
        ),
    )
    traceability.create(
        project.project_id,
        RequirementAllocationCreate(
            requirement_id="COM-001",
            component_id="COM-001",
            rationale="Communications unit owns the data transmission function.",
            allocated_by="Test systems engineer",
        ),
    )
    app.dependency_overrides[get_revision_impact_store] = lambda: RevisionImpactStore(database)
    return project, projects, spacecraft


def clear_overrides() -> None:
    app.dependency_overrides.pop(get_revision_impact_store, None)
    app.dependency_overrides.pop(get_requirement_traceability_store, None)


def test_change_impact_compares_requirements_components_and_allocations(tmp_path) -> None:
    project, projects, spacecraft = setup_project(tmp_path)
    try:
        updated_mission = mission_payload()
        updated_mission["requirements"][0]["title"] = "Acquire calibrated images"
        updated_mission["requirements"][0]["acceptance_criteria"] = "A calibrated image test demonstrates acquisition."
        updated_mission["requirements"].pop(1)
        updated_mission["requirements"].append({
            "requirement_id": "NAV-001",
            "title": "Determine orbit",
            "statement": "The spacecraft shall determine its orbit state.",
            "category": "navigation",
            "verification_method": "analysis",
            "acceptance_criteria": "An orbit determination analysis demonstrates the required state accuracy.",
        })
        projects.create_revision(project.project_id, MissionProjectDraft.model_validate(updated_mission))
        spacecraft.create_revision(
            project.project_id,
            SpacecraftConfigurationDraft.model_validate(spacecraft_payload(["PAY-001", "THERM-001"], payload_mass=5.0)),
        )

        response = client.get(
            f"/api/v1/missions/projects/{project.project_id}/traceability/change-impact",
            params={
                "baseline_mission_revision": 1,
                "target_mission_revision": 2,
                "baseline_spacecraft_revision": 1,
                "target_spacecraft_revision": 2,
            },
        )
        assert response.status_code == 200
        report = response.json()
        assert report["added_requirement_count"] == 1
        assert report["removed_requirement_count"] == 1
        assert report["modified_requirement_count"] == 1
        assert report["added_component_count"] == 1
        assert report["removed_component_count"] == 1
        assert report["modified_component_count"] == 1

        changed_requirement = next(item for item in report["requirement_changes"] if item["requirement_id"] == "SCI-001")
        assert changed_requirement["change_type"] == "modified"
        assert "acceptance_criteria" in changed_requirement["changed_fields"]
        changed_component = next(item for item in report["component_changes"] if item["component_id"] == "PAY-001")
        assert changed_component["change_type"] == "modified"
        assert "mass" in changed_component["changed_fields"]
        assert len(report["impacted_allocations"]) == 2
    finally:
        clear_overrides()


def test_same_revision_comparison_returns_no_changes(tmp_path) -> None:
    project, _, _ = setup_project(tmp_path)
    try:
        response = client.get(
            f"/api/v1/missions/projects/{project.project_id}/traceability/change-impact",
            params={
                "baseline_mission_revision": 1,
                "target_mission_revision": 1,
                "baseline_spacecraft_revision": 1,
                "target_spacecraft_revision": 1,
            },
        )
        assert response.status_code == 200
        assert response.json()["requirement_changes"] == []
        assert response.json()["component_changes"] == []
        assert response.json()["impacted_allocations"] == []
    finally:
        clear_overrides()


def test_change_impact_rejects_target_before_baseline(tmp_path) -> None:
    project, _, _ = setup_project(tmp_path)
    try:
        response = client.get(
            f"/api/v1/missions/projects/{project.project_id}/traceability/change-impact",
            params={
                "baseline_mission_revision": 2,
                "target_mission_revision": 1,
                "baseline_spacecraft_revision": 1,
                "target_spacecraft_revision": 1,
            },
        )
        assert response.status_code == 422
    finally:
        clear_overrides()


def test_change_impact_rejects_missing_revision(tmp_path) -> None:
    project, _, _ = setup_project(tmp_path)
    try:
        response = client.get(
            f"/api/v1/missions/projects/{project.project_id}/traceability/change-impact",
            params={
                "baseline_mission_revision": 1,
                "target_mission_revision": 9,
                "baseline_spacecraft_revision": 1,
                "target_spacecraft_revision": 2,
            },
        )
        assert response.status_code == 404
    finally:
        clear_overrides()


def test_change_impact_returns_404_for_unknown_project(tmp_path) -> None:
    database = tmp_path / "unknown.sqlite3"
    MissionProjectStore(database)
    app.dependency_overrides[get_revision_impact_store] = lambda: RevisionImpactStore(database)
    try:
        response = client.get(
            "/api/v1/missions/projects/00000000-0000-0000-0000-000000000000/traceability/change-impact",
            params={
                "baseline_mission_revision": 1,
                "target_mission_revision": 1,
                "baseline_spacecraft_revision": 1,
                "target_spacecraft_revision": 1,
            },
        )
        assert response.status_code == 404
    finally:
        clear_overrides()
