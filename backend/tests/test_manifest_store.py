from fastapi.testclient import TestClient

from app.engineering.routes import get_manifest_store
from app.main import app
from app.storage.manifests import ManifestStore

client = TestClient(app)


def manifest_payload(manifest_id: str = "lro-test-product-v1") -> dict:
    return {
        "manifest_id": manifest_id,
        "title": "Synthetic lunar terrain test raster",
        "provider": "ORBITOPS test fixture",
        "product_id": "synthetic-terrain-001",
        "release_or_version": "1.0",
        "source_url": "https://example.org/data/terrain.tif",
        "citation_text": "Synthetic test fixture; not an external science product.",
        "retrieved_at": "2026-11-12T10:00:00Z",
        "file_name": "terrain.tif",
        "media_type": "image/tiff",
        "data_format": "GeoTIFF",
        "file_size_bytes": 1024,
        "checksum_sha256": "a" * 64,
        "license_or_terms": "Synthetic fixture; no external data rights implied",
        "access_classification": "unknown",
        "coordinate_reference_frame": "Not specified for synthetic fixture",
        "time_system": "Not applicable",
        "variable_units": {"elevation": "m"},
        "notes": "Test metadata only; not a NASA data product.",
    }


def test_manifest_create_get_and_persistence(tmp_path) -> None:
    database_path = tmp_path / "orbitops-test.sqlite3"
    store = ManifestStore(database_path)
    app.dependency_overrides[get_manifest_store] = lambda: store
    try:
        created = client.post("/api/v1/datasets/manifests", json=manifest_payload())
        assert created.status_code == 201
        assert created.json()["manifest_id"] == "lro-test-product-v1"

        retrieved = client.get("/api/v1/datasets/manifests/lro-test-product-v1")
        assert retrieved.status_code == 200
        assert retrieved.json()["checksum_sha256"] == "a" * 64

        reopened_store = ManifestStore(database_path)
        persisted = reopened_store.get("lro-test-product-v1")
        assert persisted is not None
        assert persisted.product_id == "synthetic-terrain-001"
    finally:
        app.dependency_overrides.pop(get_manifest_store, None)


def test_manifest_duplicate_identifier_returns_conflict(tmp_path) -> None:
    store = ManifestStore(tmp_path / "orbitops-test.sqlite3")
    app.dependency_overrides[get_manifest_store] = lambda: store
    try:
        first = client.post("/api/v1/datasets/manifests", json=manifest_payload())
        duplicate = client.post("/api/v1/datasets/manifests", json=manifest_payload())
        assert first.status_code == 201
        assert duplicate.status_code == 409
    finally:
        app.dependency_overrides.pop(get_manifest_store, None)


def test_manifest_list_supports_limit_and_offset(tmp_path) -> None:
    store = ManifestStore(tmp_path / "orbitops-test.sqlite3")
    app.dependency_overrides[get_manifest_store] = lambda: store
    try:
        first = client.post("/api/v1/datasets/manifests", json=manifest_payload("product-a"))
        second = client.post("/api/v1/datasets/manifests", json=manifest_payload("product-b"))
        assert first.status_code == 201
        assert second.status_code == 201

        response = client.get("/api/v1/datasets/manifests?limit=1&offset=1")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["manifest_id"] == "product-b"
    finally:
        app.dependency_overrides.pop(get_manifest_store, None)


def test_unknown_manifest_returns_not_found(tmp_path) -> None:
    store = ManifestStore(tmp_path / "orbitops-test.sqlite3")
    app.dependency_overrides[get_manifest_store] = lambda: store
    try:
        response = client.get("/api/v1/datasets/manifests/not-registered")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_manifest_store, None)
