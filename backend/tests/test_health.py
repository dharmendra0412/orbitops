from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_process_liveness() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "orbitops-api"}


def test_system_does_not_claim_validated_models() -> None:
    response = client.get("/api/v1/system")

    assert response.status_code == 200
    body = response.json()
    assert body["scientific_model_status"] == "not_yet_released"
    assert body["validation_policy"] == "evidence_required"
