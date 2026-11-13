from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app
from app.missions.projects import MissionProjectDraft
from app.missions.project_routes import get_mission_project_store
from app.storage.mission_projects import MissionProjectStore

client = TestClient(app)


def mission_payload(name: str = "Lunar polar lander concept") -> dict:
    return {
        "name": name,
        "summary": "Preliminary mission definition for a robotic lunar polar lander.",
        "target_body": "Moon",
        "mission_archetype": "lander",
        "primary_objective": "Characterize selected surface and subsurface properties at a candidate lunar polar site.",
        "intended_users": ["students", "researchers"],
        "requirements": [
            {
                "requirement_id": "SCI-001",
                "title": "Acquire surface imagery",
                "statement": "The payload shall acquire image data from the landing site.",
                "category": "science",
                "verification_method": "analysis",
                "acceptance_criteria": "Image acquisition performance is evaluated against a documented payload specification.",
                "source_reference": "TBD: instrument specification",
            }
        ],
    }


def test_create_and_get_mission_project_with_first_revision(tmp_path) -> None:
    store = MissionProjectStore(tmp_path / "mission-projects.sqlite3")
    app.dependency_overrides[get_mission_project_store] = lambda: store
    try:
        created = client.post("/api/v1/missions/projects", json=mission_payload())
        assert created.status_code == 201
        body = created.json()
        assert body["latest_revision"] == 1
        assert body["revision"]["revision_number"] == 1
        assert body["revision"]["draft"]["target_body"] == "Moon"

        retrieved = client.get(f"/api/v1/missions/projects/{body['project_id']}")
        assert retrieved.status_code == 200
        assert retrieved.json()["revision"]["draft"]["requirements"][0]["requirement_id"] == "SCI-001"
    finally:
        app.dependency_overrides.pop(get_mission_project_store, None)


def test_new_revision_is_append_only_and_becomes_latest(tmp_path) -> None:
    store = MissionProjectStore(tmp_path / "mission-projects.sqlite3")
    app.dependency_overrides[get_mission_project_store] = lambda: store
    try:
        created = client.post("/api/v1/missions/projects", json=mission_payload())
        project_id = created.json()["project_id"]

        revised = client.post(
            f"/api/v1/missions/projects/{project_id}/revisions",
            json=mission_payload("Lunar polar lander concept - revised"),
        )
        assert revised.status_code == 201
        assert revised.json()["latest_revision"] == 2
        assert revised.json()["revision"]["revision_number"] == 2

        with store._connection() as connection:
            rows = connection.execute(
                "SELECT revision_number FROM mission_project_revisions WHERE project_id = ? ORDER BY revision_number",
                (project_id,),
            ).fetchall()
        assert [row["revision_number"] for row in rows] == [1, 2]
    finally:
        app.dependency_overrides.pop(get_mission_project_store, None)


def test_list_mission_projects_supports_pagination(tmp_path) -> None:
    store = MissionProjectStore(tmp_path / "mission-projects.sqlite3")
    app.dependency_overrides[get_mission_project_store] = lambda: store
    try:
        first = client.post("/api/v1/missions/projects", json=mission_payload("Mission Alpha"))
        second = client.post("/api/v1/missions/projects", json=mission_payload("Mission Bravo"))
        assert first.status_code == 201
        assert second.status_code == 201

        response = client.get("/api/v1/missions/projects?limit=1&offset=0")
        assert response.status_code == 200
        assert len(response.json()) == 1
    finally:
        app.dependency_overrides.pop(get_mission_project_store, None)


def test_unknown_mission_project_returns_404() -> None:
    response = client.get("/api/v1/missions/projects/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_mission_project_rejects_unknown_fields() -> None:
    payload = mission_payload()
    payload["unreviewed_flight_ready"] = True
    response = client.post("/api/v1/missions/projects", json=payload)
    assert response.status_code == 422


def test_concurrent_revisions_are_serialized_without_gaps_or_duplicates(tmp_path) -> None:
    store = MissionProjectStore(tmp_path / "mission-projects.sqlite3")
    created = store.create(
        MissionProjectDraft.model_validate(
            mission_payload()
        )
    )

    revision_count = 8
    with ThreadPoolExecutor(max_workers=revision_count) as executor:
        records = list(
            executor.map(
                lambda index: store.create_revision(
                    created.project_id,
                    __import__("app.missions.projects", fromlist=["MissionProjectDraft"]).MissionProjectDraft.model_validate(
                        mission_payload(f"Concurrent revision {index}")
                    ),
                ),
                range(revision_count),
            )
        )

    assert sorted(record.latest_revision for record in records) == list(
        range(2, revision_count + 2)
    )
    latest = store.get(created.project_id)
    assert latest is not None
    assert latest.latest_revision == revision_count + 1

    with store._connection() as connection:
        rows = connection.execute(
            "SELECT revision_number FROM mission_project_revisions "
            "WHERE project_id = ? ORDER BY revision_number",
            (str(created.project_id),),
        ).fetchall()
    assert [row["revision_number"] for row in rows] == list(
        range(1, revision_count + 2)
    )
