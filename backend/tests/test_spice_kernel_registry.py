from fastapi.testclient import TestClient

from app.ephemeris.routes import get_spice_kernel_store
from app.main import app
from app.storage.spice_kernels import SpiceKernelStore

client = TestClient(app)


def payload(kernel_id: str = "naif0012.tls") -> dict:
    return {
        "kernel_id": kernel_id,
        "file_name": "naif0012.tls",
        "kernel_type": "LSK",
        "source_url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls",
        "provider": "NASA Navigation and Ancillary Information Facility",
        "release_or_version": "NAIF generic LSK naif0012",
        "sha256": "A" * 64,
        "coverage_start": "2000-01-01T00:00:00Z",
        "coverage_end": "2030-01-01T00:00:00Z",
        "time_system": "TDB",
        "reference_frames": ["J2000"],
        "target_names": [],
        "license_or_terms": "Provider terms must be reviewed by the user.",
    }


def configure_store(tmp_path):
    store = SpiceKernelStore(tmp_path / "spice-kernels.sqlite3")
    app.dependency_overrides[get_spice_kernel_store] = lambda: store
    return store


def clear_overrides():
    app.dependency_overrides.pop(get_spice_kernel_store, None)


def test_register_and_retrieve_kernel_metadata_without_claiming_validation(tmp_path):
    configure_store(tmp_path)
    try:
        created = client.post("/api/v1/ephemeris/spice/kernels", json=payload())
        assert created.status_code == 201
        body = created.json()
        assert body["registration"]["sha256"] == "a" * 64
        assert body["metadata_status"] == "user_declared_unverified"
        assert "has not been computed" in body["limitations"][0]

        retrieved = client.get("/api/v1/ephemeris/spice/kernels/naif0012.tls")
        assert retrieved.status_code == 200
        assert retrieved.json()["registration"]["kernel_type"] == "LSK"
    finally:
        clear_overrides()


def test_kernel_registration_is_append_only_and_rejects_duplicate_ids(tmp_path):
    configure_store(tmp_path)
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=payload()).status_code == 201
        duplicate = client.post("/api/v1/ephemeris/spice/kernels", json=payload())
        assert duplicate.status_code == 409
    finally:
        clear_overrides()


def test_kernel_registry_lists_with_pagination(tmp_path):
    configure_store(tmp_path)
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=payload("kernel-a")).status_code == 201
        second = payload("kernel-b")
        second["file_name"] = "de440s.bsp"
        second["kernel_type"] = "SPK"
        assert client.post("/api/v1/ephemeris/spice/kernels", json=second).status_code == 201
        response = client.get("/api/v1/ephemeris/spice/kernels?limit=1&offset=1")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["registration"]["kernel_id"] == "kernel-b"
    finally:
        clear_overrides()


def test_kernel_registration_rejects_invalid_hash_and_path_like_filename():
    invalid_hash = payload()
    invalid_hash["sha256"] = "not-a-hash"
    assert client.post("/api/v1/ephemeris/spice/kernels", json=invalid_hash).status_code == 422

    invalid_name = payload()
    invalid_name["file_name"] = "../naif0012.tls"
    assert client.post("/api/v1/ephemeris/spice/kernels", json=invalid_name).status_code == 422


def test_kernel_coverage_requires_timezone_and_ordered_bounds():
    invalid = payload()
    invalid["coverage_start"] = "2031-01-01T00:00:00Z"
    assert client.post("/api/v1/ephemeris/spice/kernels", json=invalid).status_code == 422

    missing_pair = payload()
    missing_pair["coverage_end"] = None
    assert client.post("/api/v1/ephemeris/spice/kernels", json=missing_pair).status_code == 422


def test_kernel_not_found_returns_404(tmp_path):
    configure_store(tmp_path)
    try:
        response = client.get("/api/v1/ephemeris/spice/kernels/unknown-kernel")
        assert response.status_code == 404
    finally:
        clear_overrides()
