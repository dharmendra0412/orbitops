from fastapi.testclient import TestClient

from app.main import app
from app.missions.model_governance_routes import get_model_governance_store
from app.storage.model_governance import ModelGovernanceStore

client = TestClient(app)

MODEL_ID = "propulsion.ideal-rocket-equation"
MODEL_VERSION = "0.1.0"
EQUATION_ID = "PROPULSION.IDEAL_ROCKET_EQUATION.V1"


def configured_store(tmp_path):
    store = ModelGovernanceStore(tmp_path / "model-governance.sqlite3")
    app.dependency_overrides[get_model_governance_store] = lambda: store
    return store


def clear_overrides() -> None:
    app.dependency_overrides.pop(get_model_governance_store, None)


def assessment_payload(kind: str, outcome: str = "pass") -> dict:
    return {
        "model_id": MODEL_ID,
        "model_version": MODEL_VERSION,
        "equation_id": EQUATION_ID,
        "kind": kind,
        "outcome": outcome,
        "method": "test" if kind == "verification" else "comparison",
        "performed_at": "2026-11-13T10:00:00Z",
        "performed_by": "Model governance test fixture",
        "summary": "Synthetic assessment record for automated API tests only.",
        "evidence_reference": "test-artifact://model-governance/evidence-001",
    }


def test_registered_models_start_unvalidated(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        response = client.get("/api/v1/models/governance/catalog")
        assert response.status_code == 200
        models = response.json()["models"]
        assert len(models) == 3
        propulsion = next(item for item in models if item["model_id"] == MODEL_ID)
        assert propulsion["current_state"] == "unvalidated"
        assert propulsion["assessment_count"] == 0
    finally:
        clear_overrides()


def test_verification_and_validation_advance_derived_state(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        verification = client.post(
            "/api/v1/models/governance/assessments",
            json=assessment_payload("verification"),
        )
        assert verification.status_code == 201

        catalog = client.get("/api/v1/models/governance/catalog").json()
        propulsion = next(item for item in catalog["models"] if item["model_id"] == MODEL_ID)
        assert propulsion["current_state"] == "verified"

        validation = client.post(
            "/api/v1/models/governance/assessments",
            json=assessment_payload("validation"),
        )
        assert validation.status_code == 201

        catalog = client.get("/api/v1/models/governance/catalog").json()
        propulsion = next(item for item in catalog["models"] if item["model_id"] == MODEL_ID)
        assert propulsion["current_state"] == "validated"
        assert propulsion["assessment_count"] == 2
    finally:
        clear_overrides()


def test_failed_latest_assessment_requires_review(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        client.post(
            "/api/v1/models/governance/assessments",
            json=assessment_payload("verification"),
        )
        client.post(
            "/api/v1/models/governance/assessments",
            json=assessment_payload("validation"),
        )
        failed = assessment_payload("verification", "fail")
        failed["performed_at"] = "2026-11-13T12:00:00Z"
        failed["summary"] = "A later regression test failed and requires investigation."
        response = client.post("/api/v1/models/governance/assessments", json=failed)
        assert response.status_code == 201

        catalog = client.get("/api/v1/models/governance/catalog").json()
        propulsion = next(item for item in catalog["models"] if item["model_id"] == MODEL_ID)
        assert propulsion["current_state"] == "review_required"
        assert propulsion["latest_verification_outcome"] == "fail"
    finally:
        clear_overrides()


def test_assessment_rejects_unknown_model_version_or_equation(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        payload = assessment_payload("verification")
        payload["model_version"] = "9.9.9"
        response = client.post("/api/v1/models/governance/assessments", json=payload)
        assert response.status_code == 422
    finally:
        clear_overrides()


def test_assessment_rejects_unregistered_reference_dataset(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        payload = assessment_payload("validation")
        payload["reference_dataset_id"] = "dataset-does-not-exist"
        response = client.post("/api/v1/models/governance/assessments", json=payload)
        assert response.status_code == 422
    finally:
        clear_overrides()


def test_assessment_evidence_is_append_only_and_filterable(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        endpoint = "/api/v1/models/governance/assessments"
        first = client.post(endpoint, json=assessment_payload("verification"))
        second_payload = assessment_payload("verification", "inconclusive")
        second_payload["performed_at"] = "2026-11-13T11:00:00Z"
        second_payload["summary"] = "Additional independent evidence is required."
        second = client.post(endpoint, json=second_payload)
        assert first.status_code == 201
        assert second.status_code == 201

        listed = client.get(
            endpoint,
            params={"model_id": MODEL_ID, "model_version": MODEL_VERSION},
        )
        assert listed.status_code == 200
        assert len(listed.json()) == 2
        assert {item["outcome"] for item in listed.json()} == {"pass", "inconclusive"}
    finally:
        clear_overrides()

def test_orbital_model_equations_are_registered_for_assessment(tmp_path) -> None:
    configured_store(tmp_path)
    try:
        response = client.post(
            "/api/v1/models/governance/assessments",
            json={
                "model_id": "orbital.two-body-keplerian",
                "model_version": "0.1.0",
                "equation_id": "ORBITAL.HOHMANN.TRANSFER_DELTA_V.V1",
                "kind": "verification",
                "outcome": "inconclusive",
                "method": "analysis",
                "performed_at": "2026-11-13T10:00:00Z",
                "performed_by": "Orbital model test reviewer",
                "summary": "Preliminary analytic checks recorded; independent validation remains pending.",
                "evidence_reference": "test-artifact://orbital-model/verification-001",
            },
        )
        assert response.status_code == 201
        catalog = client.get("/api/v1/models/governance/catalog").json()
        orbital = next(item for item in catalog["models"] if item["model_id"] == "orbital.two-body-keplerian")
        assert orbital["current_state"] == "review_required"
    finally:
        clear_overrides()
