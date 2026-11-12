from hashlib import sha256

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_checksum_endpoint_returns_file_integrity_metadata() -> None:
    content = b"ORBITOPS synthetic integrity fixture"
    response = client.post(
        "/api/v1/datasets/checksum",
        files={"file": ("fixture.bin", content, "application/octet-stream")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file_name"] == "fixture.bin"
    assert body["file_size_bytes"] == len(content)
    assert body["checksum_sha256"] == sha256(content).hexdigest()
    assert body["storage_status"] == "not_persisted"


def test_checksum_endpoint_rejects_empty_file() -> None:
    response = client.post(
        "/api/v1/datasets/checksum",
        files={"file": ("empty.bin", b"", "application/octet-stream")},
    )

    assert response.status_code == 422


def test_checksum_endpoint_rejects_path_like_filename() -> None:
    response = client.post(
        "/api/v1/datasets/checksum",
        files={"file": ("../fixture.bin", b"data", "application/octet-stream")},
    )

    assert response.status_code == 400
