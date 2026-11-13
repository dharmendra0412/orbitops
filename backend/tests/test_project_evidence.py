from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.missions.model_governance import ModelAssessmentCreate
from app.missions.model_governance_routes import get_model_governance_store
from app.missions.project_evidence_routes import get_mission_evidence_store
from app.missions.projects import MissionProjectDraft
from app.storage.manifests import ManifestStore
from app.storage.mission_evidence import MissionEvidenceStore
from app.storage.mission_projects import MissionProjectStore
from app.storage.model_governance import ModelGovernanceStore

client = TestClient(app)


def mission_payload() -> dict:
    return {
        "name": "Project evidence association test",
        "summary": "Mission fixture for linking reusable evidence records.",
        "target_body": "Mars",
        "mission_archetype": "orbiter",
        "primary_objective": "Acquire and return scientific observations from a planetary orbit.",
        "requirements": [],
    }


def dataset_manifest_payload() -> dict:
    return {
        "manifest_id": "PDS-TEST-001",
        "title": "Synthetic planetary test dataset",
        "provider": "Test Archive",
        "product_id": "TEST-PRODUCT-001",
        "release_or_version": "1.0",
        "source_url": "https://example.org/datasets/TEST-PRODUCT-001",
        "citation_text": "Synthetic dataset citation for automated testing.",
        "retrieved_at": "2026-11-13T10:00:00Z",
        "file_name": "test-product.dat",
        "media_type": "application/octet-stream",
        "data_format": "binary-test",
        "file_size_bytes": 128,
        "checksum_sha256": "a" * 64,
        "license_or_terms": "Synthetic test terms",
        "access_classification": "public",
        "asset_stage": "source",
        "limitations": ["Synthetic fixture; not scientific data."],
    }


def assessment_payload() -> dict:
    return {
        "model_id": "propulsion.ideal-rocket-equation",
        "model_version": "0.1.0",
        "equation_id": "PROPULSION.IDEAL_ROCKET_EQUATION.V1",
        "kind": "verification",
        "outcome": "pass",
        "method": "test",
        "performed_at": "2026-11-13T10:00:00Z",
        "performed_by": "Test reviewer",
        "summary": "Synthetic model verification evidence for association testing.",
        "evidence_reference": "test-artifact://project-evidence/model-check-001",
    }


def setup_stores(tmp_path):
    database = tmp_path / "project-evidence.sqlite3"
    projects = MissionProjectStore(database)
    manifests = ManifestStore(database)
    governance = ModelGovernanceStore(database)
    evidence = MissionEvidenceStore(database)
    project = projects.create(MissionProjectDraft.model_validate(mission_payload()))
    manifests.create(__import__("app.ingestion.manifests", fromlist=["DatasetManifest"]).DatasetManifest.model_validate(dataset_manifest_payload()))
    assessment = governance.create(ModelAssessmentCreate.model_validate(assessment_payload()))
    app.dependency_overrides[get_mission_evidence_store] = lambda: evidence
    app.dependency_overrides[get_model_governance_store] = lambda: governance
    return project, evidence, assessment


def clear_overrides() -> None:
    app.dependency_overrides.pop(get_mission_evidence_store, None)
    app.dependency_overrides.pop(get_model_governance_store, None)


def test_link_and_list_project_dataset_manifest(tmp_path) -> None:
    project, _, _ = setup_stores(tmp_path)
    try:
        endpoint = f"/api/v1/missions/projects/{project.project_id}/evidence/datasets"
        payload = {
            "manifest_id": "PDS-TEST-001",
            "purpose": "Reference dataset for the mission science environment.",
            "linked_by": "Systems engineering test fixture",
        }
        created = client.post(endpoint, json=payload)
        assert created.status_code == 201
        assert created.json()["manifest"]["product_id"] == "TEST-PRODUCT-001"
        listed = client.get(endpoint)
        assert listed.status_code == 200
        assert len(listed.json()) == 1
    finally:
        clear_overrides()


def test_dataset_link_rejects_duplicates_and_unknown_manifests(tmp_path) -> None:
    project, _, _ = setup_stores(tmp_path)
    try:
        endpoint = f"/api/v1/missions/projects/{project.project_id}/evidence/datasets"
        payload = {
            "manifest_id": "PDS-TEST-001",
            "purpose": "Reference dataset for the mission science environment.",
            "linked_by": "Systems engineering test fixture",
        }
        assert client.post(endpoint, json=payload).status_code == 201
        assert client.post(endpoint, json=payload).status_code == 409
        payload["manifest_id"] = "UNKNOWN-DATASET"
        assert client.post(endpoint, json=payload).status_code == 404
    finally:
        clear_overrides()


def test_link_and_list_model_assessment(tmp_path) -> None:
    project, _, assessment = setup_stores(tmp_path)
    try:
        endpoint = f"/api/v1/missions/projects/{project.project_id}/evidence/model-assessments"
        payload = {
            "assessment_id": str(assessment.assessment_id),
            "rationale": "This model verification record supports the mission propulsion analysis workflow.",
            "linked_by": "Systems engineering test fixture",
        }
        created = client.post(endpoint, json=payload)
        assert created.status_code == 201
        assert created.json()["assessment"]["model_id"] == "propulsion.ideal-rocket-equation"
        listed = client.get(endpoint)
        assert listed.status_code == 200
        assert len(listed.json()) == 1
    finally:
        clear_overrides()


def test_model_assessment_link_rejects_duplicates_and_unknown_assessments(tmp_path) -> None:
    project, _, assessment = setup_stores(tmp_path)
    try:
        endpoint = f"/api/v1/missions/projects/{project.project_id}/evidence/model-assessments"
        payload = {
            "assessment_id": str(assessment.assessment_id),
            "rationale": "This model verification record supports the mission propulsion analysis workflow.",
            "linked_by": "Systems engineering test fixture",
        }
        assert client.post(endpoint, json=payload).status_code == 201
        assert client.post(endpoint, json=payload).status_code == 409
        payload["assessment_id"] = str(uuid4())
        assert client.post(endpoint, json=payload).status_code == 404
    finally:
        clear_overrides()


def test_project_evidence_lists_return_404_for_unknown_project(tmp_path) -> None:
    _, _, _ = setup_stores(tmp_path)
    try:
        project_id = "00000000-0000-0000-0000-000000000000"
        assert client.get(f"/api/v1/missions/projects/{project_id}/evidence/datasets").status_code == 404
        assert client.get(f"/api/v1/missions/projects/{project_id}/evidence/model-assessments").status_code == 404
    finally:
        clear_overrides()
