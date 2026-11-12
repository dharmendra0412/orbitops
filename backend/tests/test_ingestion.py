import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.ingestion.manifests import DatasetManifest
from app.main import app

client = TestClient(app)


def valid_manifest() -> dict:
    return {
        "manifest_id": "nasa-demo-product-v1",
        "title": "Synthetic lunar terrain test raster",
        "provider": "ORBITOPS test fixture",
        "product_id": "synthetic-terrain-001",
        "release_or_version": "1.0",
        "source_url": "https://example.org/data/terrain.tif",
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


def test_valid_dataset_manifest_is_accepted_by_api() -> None:
    response = client.post("/api/v1/datasets/manifests/validate", json=valid_manifest())

    assert response.status_code == 200
    assert response.json()["manifest_id"] == "nasa-demo-product-v1"
    assert response.json()["checksum_sha256"] == "a" * 64


def test_manifest_rejects_invalid_sha256() -> None:
    payload = valid_manifest()
    payload["checksum_sha256"] = "not-a-checksum"

    with pytest.raises(ValidationError):
        DatasetManifest.model_validate(payload)


def test_manifest_rejects_path_in_file_name() -> None:
    payload = valid_manifest()
    payload["file_name"] = "../terrain.tif"

    with pytest.raises(ValidationError):
        DatasetManifest.model_validate(payload)


def test_manifest_rejects_reversed_temporal_coverage() -> None:
    payload = valid_manifest()
    payload["temporal_coverage_start"] = "2026-11-13T00:00:00Z"
    payload["temporal_coverage_end"] = "2026-11-12T00:00:00Z"

    with pytest.raises(ValidationError):
        DatasetManifest.model_validate(payload)


def test_manifest_rejects_unknown_fields() -> None:
    payload = valid_manifest()
    payload["invented_accuracy"] = 0.01

    with pytest.raises(ValidationError):
        DatasetManifest.model_validate(payload)
