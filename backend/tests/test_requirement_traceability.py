from fastapi.testclient import TestClient

from app.main import app
from app.missions.project_routes import get_mission_project_store
from app.missions.projects import MissionProjectDraft
from app.missions.spacecraft import SpacecraftConfigurationDraft
from app.missions.traceability_routes import get_requirement_traceability_store
from app.missions.verification import VerificationRecordCreate
from app.storage.mission_projects import MissionProjectStore
from app.storage.mission_verification import MissionVerificationStore
from app.storage.requirement_traceability import RequirementTraceabilityStore
from app.storage.spacecraft_configurations import SpacecraftConfigurationStore

client = TestClient(app)


def mission_payload() -> dict:
    return {
        "name": "Mars science orbiter",
        "summary": "Preliminary mission for traceability testing.",
        "target_body": "Mars",
        "mission_archetype": "orbiter",
        "primary_objective": "Acquire science observations and return them to ground systems.",
        "requirements": [
            {
                "requirement_id": "SCI-001",
                "title": "Acquire science images",
                "statement": "The payload shall acquire images of the target region.",
                "category": "science",
                "verification_method": "test",
                "acceptance_criteria": "An approved test procedure demonstrates image acquisition.",
            },
            {
                "requirement_id": "COM-001",
                "title": "Transmit science data",
                "statement": "The spacecraft shall transmit science data to the ground segment.",
                "category": "communications",
                "verification_method": "analysis",
                "acceptance_criteria": "A documented link analysis demonstrates the required data return.",
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
        "intended_use": "Automated traceability persistence tests.",
        "credibility": "unvalidated",
        "limitations": ["Not a real spacecraft specification."],
    }


def spacecraft_payload(component_ids: list[str] | None = None) -> dict:
    ids = component_ids or ["PAY-001", "COM-001"]
    return {
        "name": "Traceability test configuration",
        "description": "Synthetic configuration for API tests.",
        "mass_margin_percent": 10.0,
        "assumptions": ["All values are synthetic test fixtures."],
        "components": [
            {
                "component_id": component_id,
                "name": component_id + " test unit",
                "subsystem": "payload" if component_id.startswith("PAY") else "communications",
                "mass": quantity("mass-" + component_id, "Component mass", 5.0, "kg", "mass"),
                "load_duty_cycle": 1.0,
                "generation_duty_cycle": 0.0,
            }
            for component_id in ids
        ],
    }


def configured_stores(tmp_path):
    database = tmp_path / "traceability.sqlite3"
    projects = MissionProjectStore(database)
    spacecraft = SpacecraftConfigurationStore(database)
    verification = MissionVerificationStore(database)
    traceability = RequirementTraceabilityStore(database)
    app.dependency_overrides[get_mission_project_store] = lambda: projects
    app.dependency_overrides[get_requirement_traceability_store] = lambda: traceability
    project = projects.create(MissionProjectDraft.model_validate(mission_payload()))
    return project, spacecraft, verification, traceability


def clear_overrides() -> None:
    app.dependency_overrides.pop(get_mission_project_store, None)
    app.dependency_overrides.pop(get_requirement_traceability_store, None)


def allocation_payload(requirement_id: str = "SCI-001", component_id: str = "PAY-001") -> dict:
    return {
        "requirement_id": requirement_id,
        "component_id": component_id,
        "rationale": "This component is the planned implementation owner for the requirement.",
        "allocated_by": "Systems engineering test fixture",
    }


def test_allocate_requirement_and_build_traceability_matrix(tmp_path) -> None:
    project, spacecraft, verification, _ = configured_stores(tmp_path)
    spacecraft.create(project.project_id, SpacecraftConfigurationDraft.model_validate(spacecraft_payload()))
    try:
        created = client.post(
            f"/api/v1/missions/projects/{project.project_id}/traceability/allocations",
            json=allocation_payload(),
        )
        assert created.status_code == 201
        assert created.json()["component_id"] == "PAY-001"

        verification.create(
            project.project_id,
            VerificationRecordCreate.model_validate({
                "requirement_id": "SCI-001",
                "method": "test",
                "outcome": "pass",
                "performed_at": "2026-11-13T10:00:00Z",
                "performed_by": "Test fixture",
                "summary": "Synthetic evidence record; not an acceptance decision.",
            }),
        )
        matrix = client.get(
            f"/api/v1/missions/projects/{project.project_id}/traceability/matrix"
        )
        assert matrix.status_code == 200
        body = matrix.json()
        assert body["requirement_count"] == 2
        assert body["allocated_requirement_count"] == 1
        assert body["unallocated_requirement_count"] == 1
        science = next(row for row in body["rows"] if row["requirement_id"] == "SCI-001")
        assert science["allocated"] is True
        assert science["active_component_count"] == 1
        assert science["pass_record_count"] == 1
        assert science["verification_evidence_present"] is True
        assert "do not prove a component satisfies" in body["limitations"][0]
    finally:
        clear_overrides()


def test_allocation_rejects_unknown_requirement(tmp_path) -> None:
    project, spacecraft, _, _ = configured_stores(tmp_path)
    spacecraft.create(project.project_id, SpacecraftConfigurationDraft.model_validate(spacecraft_payload()))
    try:
        response = client.post(
            f"/api/v1/missions/projects/{project.project_id}/traceability/allocations",
            json=allocation_payload("REQ-UNKNOWN"),
        )
        assert response.status_code == 422
    finally:
        clear_overrides()


def test_allocation_rejects_component_not_in_latest_configuration(tmp_path) -> None:
    project, spacecraft, _, _ = configured_stores(tmp_path)
    spacecraft.create(project.project_id, SpacecraftConfigurationDraft.model_validate(spacecraft_payload()))
    try:
        response = client.post(
            f"/api/v1/missions/projects/{project.project_id}/traceability/allocations",
            json=allocation_payload(component_id="THERMAL-404"),
        )
        assert response.status_code == 422
    finally:
        clear_overrides()


def test_allocation_requires_spacecraft_configuration(tmp_path) -> None:
    project, _, _, _ = configured_stores(tmp_path)
    try:
        response = client.post(
            f"/api/v1/missions/projects/{project.project_id}/traceability/allocations",
            json=allocation_payload(),
        )
        assert response.status_code == 409
    finally:
        clear_overrides()


def test_duplicate_allocation_returns_conflict(tmp_path) -> None:
    project, spacecraft, _, _ = configured_stores(tmp_path)
    spacecraft.create(project.project_id, SpacecraftConfigurationDraft.model_validate(spacecraft_payload()))
    try:
        endpoint = f"/api/v1/missions/projects/{project.project_id}/traceability/allocations"
        assert client.post(endpoint, json=allocation_payload()).status_code == 201
        assert client.post(endpoint, json=allocation_payload()).status_code == 409
    finally:
        clear_overrides()


def test_removed_component_is_flagged_as_stale(tmp_path) -> None:
    project, spacecraft, _, _ = configured_stores(tmp_path)
    spacecraft.create(project.project_id, SpacecraftConfigurationDraft.model_validate(spacecraft_payload()))
    try:
        created = client.post(
            f"/api/v1/missions/projects/{project.project_id}/traceability/allocations",
            json=allocation_payload(),
        )
        assert created.status_code == 201
        spacecraft.create_revision(
            project.project_id,
            SpacecraftConfigurationDraft.model_validate(spacecraft_payload(["COM-001"])),
        )
        matrix = client.get(
            f"/api/v1/missions/projects/{project.project_id}/traceability/matrix"
        )
        science = next(row for row in matrix.json()["rows"] if row["requirement_id"] == "SCI-001")
        assert science["allocated"] is True
        assert science["active_component_count"] == 0
        assert science["stale_component_ids"] == ["PAY-001"]
    finally:
        clear_overrides()


def test_matrix_for_unknown_project_returns_404() -> None:
    response = client.get(
        "/api/v1/missions/projects/00000000-0000-0000-0000-000000000000/traceability/matrix"
    )
    assert response.status_code == 404
