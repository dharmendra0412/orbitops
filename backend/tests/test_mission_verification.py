from fastapi.testclient import TestClient

from app.main import app
from app.missions.project_routes import get_mission_project_store
from app.missions.verification_routes import get_mission_verification_store
from app.storage.mission_projects import MissionProjectStore
from app.storage.mission_verification import MissionVerificationStore

client = TestClient(app)


def mission_payload() -> dict:
    return {
        "name": "Lunar polar lander verification demo",
        "summary": "Test mission definition for verification evidence.",
        "target_body": "Moon",
        "mission_archetype": "lander",
        "primary_objective": "Demonstrate requirement evidence capture for a lunar lander concept.",
        "requirements": [
            {
                "requirement_id": "SCI-001",
                "title": "Acquire surface imagery",
                "statement": "The payload shall acquire image data from the landing site.",
                "category": "science",
                "verification_method": "test",
                "acceptance_criteria": "The test report shall demonstrate image acquisition against the approved payload specification.",
            }
        ],
    }


def evidence_payload() -> dict:
    return {
        "requirement_id": "SCI-001",
        "method": "test",
        "outcome": "pass",
        "performed_at": "2026-11-12T10:00:00Z",
        "performed_by": "Integration test fixture",
        "summary": "Synthetic evidence record used to verify API persistence.",
        "evidence_reference": "https://example.org/test-evidence/SCI-001",
    }


def configured_stores(tmp_path):
    database_path = tmp_path / "mission-verification.sqlite3"
    project_store = MissionProjectStore(database_path)
    verification_store = MissionVerificationStore(database_path)
    app.dependency_overrides[get_mission_project_store] = lambda: project_store
    app.dependency_overrides[get_mission_verification_store] = lambda: verification_store
    return project_store, verification_store


def clear_overrides() -> None:
    app.dependency_overrides.pop(get_mission_project_store, None)
    app.dependency_overrides.pop(get_mission_verification_store, None)


def test_create_and_list_requirement_verification_record(tmp_path) -> None:
    configured_stores(tmp_path)
    try:
        project = client.post("/api/v1/missions/projects", json=mission_payload())
        assert project.status_code == 201
        project_id = project.json()["project_id"]

        created = client.post(
            f"/api/v1/missions/projects/{project_id}/verification-records",
            json=evidence_payload(),
        )
        assert created.status_code == 201
        assert created.json()["outcome"] == "pass"
        assert created.json()["requirement_id"] == "SCI-001"

        listed = client.get(f"/api/v1/missions/projects/{project_id}/verification-records")
        assert listed.status_code == 200
        assert len(listed.json()) == 1
    finally:
        clear_overrides()


def test_verification_rejects_unknown_requirement(tmp_path) -> None:
    configured_stores(tmp_path)
    try:
        project = client.post("/api/v1/missions/projects", json=mission_payload())
        project_id = project.json()["project_id"]
        payload = evidence_payload()
        payload["requirement_id"] = "UNKNOWN-999"
        response = client.post(
            f"/api/v1/missions/projects/{project_id}/verification-records",
            json=payload,
        )
        assert response.status_code == 422
    finally:
        clear_overrides()


def test_verification_rejects_method_mismatch(tmp_path) -> None:
    configured_stores(tmp_path)
    try:
        project = client.post("/api/v1/missions/projects", json=mission_payload())
        project_id = project.json()["project_id"]
        payload = evidence_payload()
        payload["method"] = "inspection"
        response = client.post(
            f"/api/v1/missions/projects/{project_id}/verification-records",
            json=payload,
        )
        assert response.status_code == 422
    finally:
        clear_overrides()


def test_verification_records_are_append_only(tmp_path) -> None:
    configured_stores(tmp_path)
    try:
        project = client.post("/api/v1/missions/projects", json=mission_payload())
        project_id = project.json()["project_id"]
        first = client.post(
            f"/api/v1/missions/projects/{project_id}/verification-records",
            json=evidence_payload(),
        )
        second_payload = evidence_payload()
        second_payload["outcome"] = "inconclusive"
        second_payload["performed_at"] = "2026-11-13T10:00:00Z"
        second_payload["summary"] = "Follow-up review requires additional test evidence."
        second = client.post(
            f"/api/v1/missions/projects/{project_id}/verification-records",
            json=second_payload,
        )
        assert first.status_code == 201
        assert second.status_code == 201

        listed = client.get(f"/api/v1/missions/projects/{project_id}/verification-records")
        assert listed.status_code == 200
        assert len(listed.json()) == 2
        assert {item["outcome"] for item in listed.json()} == {"pass", "inconclusive"}
    finally:
        clear_overrides()


def test_verification_requires_existing_project() -> None:
    response = client.get(
        "/api/v1/missions/projects/00000000-0000-0000-0000-000000000000/verification-records"
    )
    assert response.status_code == 404
