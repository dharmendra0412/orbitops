from fastapi.testclient import TestClient

from app.ingestion.manifests import DatasetManifest
from app.main import app
from app.missions.model_governance import ModelAssessmentCreate
from app.missions.project_evidence import MissionDatasetLinkCreate, MissionModelAssessmentLinkCreate
from app.missions.projects import MissionProjectDraft
from app.missions.review_package_routes import (
    get_review_evidence_store,
    get_review_project_store,
    get_review_spacecraft_store,
    get_review_traceability_store,
    get_review_verification_store,
)
from app.missions.spacecraft import SpacecraftConfigurationDraft
from app.missions.traceability import RequirementAllocationCreate
from app.missions.verification import VerificationRecordCreate
from app.storage.manifests import ManifestStore
from app.storage.mission_evidence import MissionEvidenceStore
from app.storage.mission_projects import MissionProjectStore
from app.storage.mission_verification import MissionVerificationStore
from app.storage.model_governance import ModelGovernanceStore
from app.storage.requirement_traceability import RequirementTraceabilityStore
from app.storage.spacecraft_configurations import SpacecraftConfigurationStore

client = TestClient(app)


def mission_payload() -> dict:
    return {
        "name": "Review package test mission",
        "summary": "Synthetic project for review package tests.",
        "target_body": "Mars",
        "mission_archetype": "orbiter",
        "primary_objective": "Acquire science observations and return them to ground systems.",
        "requirements": [
            {
                "requirement_id": "SCI-001",
                "title": "Acquire science imagery",
                "statement": "The payload shall acquire science imagery.",
                "category": "science",
                "verification_method": "test",
                "acceptance_criteria": "A test report demonstrates image acquisition.",
            }
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
        "intended_use": "Mission review package tests.",
        "credibility": "unvalidated",
        "limitations": ["Not a real spacecraft specification."],
    }


def spacecraft_payload() -> dict:
    return {
        "name": "Review package spacecraft",
        "description": "Synthetic spacecraft configuration.",
        "mass_margin_percent": 10.0,
        "assumptions": ["Synthetic test values."],
        "components": [
            {
                "component_id": "PAY-001",
                "name": "Science payload",
                "subsystem": "payload",
                "mass": quantity("payload-mass", "Payload mass", 5.0, "kg", "mass"),
                "load_duty_cycle": 0.5,
                "generation_duty_cycle": 0.0,
            }
        ],
    }


def configured_stores(tmp_path):
    database = tmp_path / "review-package.sqlite3"
    projects = MissionProjectStore(database)
    verification = MissionVerificationStore(database)
    traceability = RequirementTraceabilityStore(database)
    spacecraft = SpacecraftConfigurationStore(database)
    evidence = MissionEvidenceStore(database)
    app.dependency_overrides[get_review_project_store] = lambda: projects
    app.dependency_overrides[get_review_verification_store] = lambda: verification
    app.dependency_overrides[get_review_traceability_store] = lambda: traceability
    app.dependency_overrides[get_review_spacecraft_store] = lambda: spacecraft
    app.dependency_overrides[get_review_evidence_store] = lambda: evidence
    project = projects.create(MissionProjectDraft.model_validate(mission_payload()))
    return project, projects, verification, traceability, spacecraft, evidence


def clear_overrides() -> None:
    app.dependency_overrides.pop(get_review_evidence_store, None)
    app.dependency_overrides.pop(get_review_project_store, None)
    app.dependency_overrides.pop(get_review_verification_store, None)
    app.dependency_overrides.pop(get_review_traceability_store, None)
    app.dependency_overrides.pop(get_review_spacecraft_store, None)


def test_review_package_reports_missing_configuration_and_evidence(tmp_path) -> None:
    project, _, _, _, _, _ = configured_stores(tmp_path)
    try:
        response = client.get(f"/api/v1/missions/projects/{project.project_id}/review-package")
        assert response.status_code == 200
        package = response.json()
        assert package["review_state"] == "incomplete"
        assert package["summary"]["requirement_count"] == 1
        assert package["summary"]["unallocated_requirement_count"] == 1
        assert package["summary"]["requirements_without_evidence_count"] == 1
        finding_codes = {item["code"] for item in package["findings"]}
        assert "SPACECRAFT_CONFIGURATION_MISSING" in finding_codes
        assert "REQUIREMENTS_UNALLOCATED" in finding_codes
        assert "VERIFICATION_EVIDENCE_MISSING" in finding_codes
    finally:
        clear_overrides()


def test_review_package_compiles_allocations_budgets_and_evidence(tmp_path) -> None:
    project, _, verification, traceability, spacecraft, _ = configured_stores(tmp_path)
    spacecraft.create(project.project_id, SpacecraftConfigurationDraft.model_validate(spacecraft_payload()))
    traceability.create(
        project.project_id,
        RequirementAllocationCreate(
            requirement_id="SCI-001",
            component_id="PAY-001",
            rationale="The science payload is the implementation owner.",
            allocated_by="Review package test fixture",
        ),
    )
    verification.create(
        project.project_id,
        VerificationRecordCreate.model_validate({
            "requirement_id": "SCI-001",
            "method": "test",
            "outcome": "pass",
            "performed_at": "2026-11-13T10:00:00Z",
            "performed_by": "Test fixture",
            "summary": "Synthetic test evidence; not an independent acceptance decision.",
        }),
    )
    try:
        response = client.get(f"/api/v1/missions/projects/{project.project_id}/review-package")
        assert response.status_code == 200
        package = response.json()
        assert package["review_state"] == "evidence_compiled"
        assert package["summary"]["allocated_requirement_count"] == 1
        assert package["summary"]["verification_record_count"] == 1
        assert package["summary"]["spacecraft_component_count"] == 1
        assert package["summary"]["linked_dataset_count"] == 0
        assert package["summary"]["linked_model_assessment_count"] == 0
        assert package["linked_datasets"] == []
        assert package["linked_model_assessments"] == []
        assert package["spacecraft_budget"]["mass"]["component_mass_kg"] == 5.0
        assert package["traceability_matrix"]["rows"][0]["pass_record_count"] == 1
        assert any("not a design approval" in item for item in package["limitations"])
    finally:
        clear_overrides()


def test_failed_evidence_requires_review(tmp_path) -> None:
    project, _, verification, traceability, spacecraft, _ = configured_stores(tmp_path)
    spacecraft.create(project.project_id, SpacecraftConfigurationDraft.model_validate(spacecraft_payload()))
    traceability.create(
        project.project_id,
        RequirementAllocationCreate(
            requirement_id="SCI-001",
            component_id="PAY-001",
            rationale="The science payload is the implementation owner.",
            allocated_by="Review package test fixture",
        ),
    )
    verification.create(
        project.project_id,
        VerificationRecordCreate.model_validate({
            "requirement_id": "SCI-001",
            "method": "test",
            "outcome": "fail",
            "performed_at": "2026-11-13T10:00:00Z",
            "performed_by": "Test fixture",
            "summary": "Synthetic failed evidence record requiring investigation.",
        }),
    )
    try:
        response = client.get(f"/api/v1/missions/projects/{project.project_id}/review-package")
        assert response.status_code == 200
        assert response.json()["review_state"] == "review_required"
        assert response.json()["summary"]["failed_verification_record_count"] == 1
    finally:
        clear_overrides()


def test_review_package_returns_404_for_unknown_project(tmp_path) -> None:
    configured_stores(tmp_path)
    try:
        response = client.get(
            "/api/v1/missions/projects/00000000-0000-0000-0000-000000000000/review-package"
        )
        assert response.status_code == 404
    finally:
        clear_overrides()


def test_review_package_includes_linked_dataset_and_model_assessment(tmp_path) -> None:
    project, _, _, _, _, evidence = configured_stores(tmp_path)
    database = tmp_path / "review-package.sqlite3"
    manifests = ManifestStore(database)
    governance = ModelGovernanceStore(database)
    manifest = DatasetManifest.model_validate({
        "manifest_id": "REVIEW-PDS-001",
        "title": "Review package reference dataset",
        "provider": "Test Archive",
        "product_id": "REVIEW-PRODUCT-001",
        "release_or_version": "1.0",
        "source_url": "https://example.org/review-product",
        "citation_text": "Synthetic reference product citation.",
        "retrieved_at": "2026-11-13T10:00:00Z",
        "file_name": "review.dat",
        "media_type": "application/octet-stream",
        "data_format": "binary-test",
        "file_size_bytes": 64,
        "checksum_sha256": "b" * 64,
        "license_or_terms": "Synthetic test terms",
        "access_classification": "public",
    })
    manifests.create(manifest)
    assessment = governance.create(ModelAssessmentCreate.model_validate({
        "model_id": "propulsion.ideal-rocket-equation",
        "model_version": "0.1.0",
        "equation_id": "PROPULSION.IDEAL_ROCKET_EQUATION.V1",
        "kind": "verification",
        "outcome": "pass",
        "method": "test",
        "performed_at": "2026-11-13T10:00:00Z",
        "performed_by": "Review package test reviewer",
        "summary": "Synthetic model verification evidence for review package inclusion.",
        "evidence_reference": "test-artifact://review-package/model-assessment",
    }))
    evidence.create_dataset_link(
        project.project_id,
        MissionDatasetLinkCreate(
            manifest_id=manifest.manifest_id,
            purpose="Reference input dataset for the mission review.",
            linked_by="Review package test fixture",
        ),
    )
    evidence.create_model_assessment_link(
        project.project_id,
        MissionModelAssessmentLinkCreate(
            assessment_id=assessment.assessment_id,
            rationale="Model verification evidence relevant to this mission's propulsion analysis.",
            linked_by="Review package test fixture",
        ),
    )
    try:
        response = client.get(f"/api/v1/missions/projects/{project.project_id}/review-package")
        assert response.status_code == 200
        package = response.json()
        assert package["summary"]["linked_dataset_count"] == 1
        assert package["summary"]["linked_model_assessment_count"] == 1
        assert package["linked_datasets"][0]["manifest"]["manifest_id"] == "REVIEW-PDS-001"
        assert package["linked_model_assessments"][0]["assessment"]["assessment_id"] == str(assessment.assessment_id)
    finally:
        clear_overrides()
