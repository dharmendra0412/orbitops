from fastapi.testclient import TestClient

from app.storage.model_runs import ModelRunStore


def test_model_run_store_persists_and_lists_snapshots(tmp_path) -> None:
    database_path = tmp_path / "model-runs.sqlite3"
    store = ModelRunStore(database_path)
    snapshot = store.create(
        model_id="test.model",
        model_version="0.1.0",
        equation_id="TEST.EQUATION.V1",
        result={"output": {"value": 42, "unit": "1"}, "inputs": [{"value_id": "test.input"}]},
    )

    reopened_store = ModelRunStore(database_path)
    retrieved = reopened_store.get(snapshot.run_id)
    listed = reopened_store.list(limit=10, offset=0)

    assert retrieved is not None
    assert retrieved.result["output"]["value"] == 42
    assert len(listed) == 1
    assert listed[0].run_id == snapshot.run_id


def test_model_run_api_retrieves_persisted_propulsion_run() -> None:
    from app.main import app

    client = TestClient(app)
    payload = {
        "dry_mass": {
            "value_id": "api.dry", "name": "Dry mass", "value": 1000, "unit": "kg",
            "dimension": "mass", "provenance": "illustrative",
            "assumption_note": "Synthetic test value.", "intended_use": "API test",
        },
        "propellant_mass": {
            "value_id": "api.propellant", "name": "Propellant mass", "value": 1000, "unit": "kg",
            "dimension": "mass", "provenance": "illustrative",
            "assumption_note": "Synthetic test value.", "intended_use": "API test",
        },
        "specific_impulse": {
            "value_id": "api.isp", "name": "Specific impulse", "value": 300, "unit": "s",
            "dimension": "time", "provenance": "illustrative",
            "assumption_note": "Synthetic test value.", "intended_use": "API test",
        },
        "intended_use": "API integration test only.",
    }

    response = client.post("/api/v1/models/propulsion/ideal-delta-v", json=payload)
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    assert run_id

    retrieved = client.get(f"/api/v1/models/runs/{run_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["model_id"] == "propulsion.ideal-rocket-equation"
    assert retrieved.json()["result"]["delta_v"]["credibility"] == "unvalidated"
