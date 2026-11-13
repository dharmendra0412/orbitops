import hashlib

import spiceypy as spice
from fastapi.testclient import TestClient

import app.ephemeris.routes as spice_routes
import app.ephemeris.time_conversion as spice_time_conversion
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


def test_kernel_registration_rejects_invalid_hash_and_path_like_filename(tmp_path):
    configure_store(tmp_path)
    try:
        invalid_hash = payload()
        invalid_hash["sha256"] = "not-a-hash"
        assert client.post("/api/v1/ephemeris/spice/kernels", json=invalid_hash).status_code == 422

        invalid_name = payload()
        invalid_name["file_name"] = "../naif0012.tls"
        assert client.post("/api/v1/ephemeris/spice/kernels", json=invalid_name).status_code == 422
    finally:
        clear_overrides()


def test_kernel_coverage_requires_timezone_and_ordered_bounds(tmp_path):
    configure_store(tmp_path)
    try:
        invalid = payload()
        invalid["coverage_start"] = "2031-01-01T00:00:00Z"
        assert client.post("/api/v1/ephemeris/spice/kernels", json=invalid).status_code == 422

        missing_pair = payload()
        missing_pair["coverage_end"] = None
        assert client.post("/api/v1/ephemeris/spice/kernels", json=missing_pair).status_code == 422
    finally:
        clear_overrides()


def test_kernel_not_found_returns_404(tmp_path):
    configure_store(tmp_path)
    try:
        response = client.get("/api/v1/ephemeris/spice/kernels/unknown-kernel")
        assert response.status_code == 404
    finally:
        clear_overrides()


def test_artifact_upload_computes_digest_and_persists_content_addressed_file(tmp_path, monkeypatch):
    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    content = b"SPICE test kernel bytes"
    registration = payload()
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        response = client.post(
            "/api/v1/ephemeris/spice/kernels/naif0012.tls/artifact",
            files={"upload": ("untrusted-name.bin", content, "application/octet-stream")},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["sha256"] == registration["sha256"]
        assert body["size_bytes"] == len(content)
        assert body["checksum_status"] == "matches_user_declared"
        artifact_path = tmp_path / "artifacts" / body["storage_key"]
        assert artifact_path.read_bytes() == content

        metadata = client.get("/api/v1/ephemeris/spice/kernels/naif0012.tls/artifact")
        assert metadata.status_code == 200
        assert metadata.json()["sha256"] == registration["sha256"]
    finally:
        clear_overrides()


def test_artifact_upload_rejects_digest_mismatch_and_leaves_no_artifact(tmp_path, monkeypatch):
    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=payload()).status_code == 201
        response = client.post(
            "/api/v1/ephemeris/spice/kernels/naif0012.tls/artifact",
            files={"upload": ("kernel.bin", b"not the declared bytes", "application/octet-stream")},
        )
        assert response.status_code == 422
        assert client.get("/api/v1/ephemeris/spice/kernels/naif0012.tls/artifact").status_code == 404
        assert not list((tmp_path / "artifacts" / ".staging").glob("*.part"))
    finally:
        clear_overrides()


def test_artifact_upload_enforces_size_limit(tmp_path, monkeypatch):
    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    monkeypatch.setattr(spice_routes, "MAX_KERNEL_UPLOAD_BYTES", 4)
    content = b"12345"
    registration = payload()
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        response = client.post(
            "/api/v1/ephemeris/spice/kernels/naif0012.tls/artifact",
            files={"upload": ("kernel.bin", content, "application/octet-stream")},
        )
        assert response.status_code == 413
        assert not list((tmp_path / "artifacts" / ".staging").glob("*.part"))
    finally:
        clear_overrides()


def test_artifact_upload_requires_registered_kernel_and_rejects_second_upload(tmp_path, monkeypatch):
    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    content = b"registered kernel bytes"
    registration = payload()
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        missing = client.post(
            "/api/v1/ephemeris/spice/kernels/missing/artifact",
            files={"upload": ("kernel.bin", content, "application/octet-stream")},
        )
        assert missing.status_code == 404

        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        first = client.post(
            "/api/v1/ephemeris/spice/kernels/naif0012.tls/artifact",
            files={"upload": ("kernel.bin", content, "application/octet-stream")},
        )
        assert first.status_code == 201
        second = client.post(
            "/api/v1/ephemeris/spice/kernels/naif0012.tls/artifact",
            files={"upload": ("kernel.bin", content, "application/octet-stream")},
        )
        assert second.status_code == 409
    finally:
        clear_overrides()


def test_artifact_upload_rejects_empty_file(tmp_path, monkeypatch):
    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    registration = payload()
    registration["sha256"] = hashlib.sha256(b"").hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        response = client.post(
            "/api/v1/ephemeris/spice/kernels/naif0012.tls/artifact",
            files={"upload": ("empty.tls", b"", "application/octet-stream")},
        )
        assert response.status_code == 422
        assert client.get("/api/v1/ephemeris/spice/kernels/naif0012.tls/artifact").status_code == 404
    finally:
        clear_overrides()


def create_test_spk(path):
    handle = spice.spkopn(str(path), "ORBITOPS REGRESSION SPK", 0)
    try:
        spice.spkw08(
            handle,
            399,
            0,
            "J2000",
            0.0,
            20.0,
            "ORBITOPS TEST SEGMENT",
            1,
            3,
            [
                [7000.0, 0.0, 0.0, 0.0, 7.5, 0.0],
                [7000.0, 75.0, 0.0, 0.0, 7.5, 0.0],
                [7000.0, 150.0, 0.0, 0.0, 7.5, 0.0],
            ],
            0.0,
            10.0,
        )
    finally:
        spice.spkcls(handle)
    return path.read_bytes()


def test_spk_inspection_detects_format_objects_and_et_coverage(tmp_path, monkeypatch):
    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    spk_path = tmp_path / "test.bsp"
    content = create_test_spk(spk_path)
    registration = payload("test-spk")
    registration["file_name"] = "test.bsp"
    registration["kernel_type"] = "SPK"
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        uploaded = client.post(
            "/api/v1/ephemeris/spice/kernels/test-spk/artifact",
            files={"upload": ("test.bsp", content, "application/octet-stream")},
        )
        assert uploaded.status_code == 201

        inspected = client.post("/api/v1/ephemeris/spice/kernels/test-spk/inspection")
        assert inspected.status_code == 201, inspected.text
        body = inspected.json()
        assert body["detected_architecture"] == "DAF"
        assert body["detected_kernel_type"] == "SPK"
        assert body["registration_type_matches"] is True
        assert body["object_ids"] == [399]
        assert body["coverage_intervals"][0]["object_id"] == 399
        assert body["coverage_intervals"][0]["intervals"][0]["start_et_seconds"] == 0.0
        assert body["coverage_intervals"][0]["intervals"][0]["end_et_seconds"] == 20.0
        assert body["toolkit_version"] == "8.4.0"
        assert client.get("/api/v1/ephemeris/spice/kernels/test-spk/inspection").status_code == 200
        assert client.post("/api/v1/ephemeris/spice/kernels/test-spk/inspection").status_code == 409
    finally:
        clear_overrides()


def test_spk_inspection_rejects_registered_type_mismatch(tmp_path, monkeypatch):
    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    spk_path = tmp_path / "test.bsp"
    content = create_test_spk(spk_path)
    registration = payload("wrong-type")
    registration["file_name"] = "test.bsp"
    registration["kernel_type"] = "PCK"
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        assert client.post(
            "/api/v1/ephemeris/spice/kernels/wrong-type/artifact",
            files={"upload": ("test.bsp", content, "application/octet-stream")},
        ).status_code == 201
        inspected = client.post("/api/v1/ephemeris/spice/kernels/wrong-type/inspection")
        assert inspected.status_code == 422
        assert client.get("/api/v1/ephemeris/spice/kernels/wrong-type/inspection").status_code == 404
    finally:
        clear_overrides()


def test_text_kernel_inspection_checks_header_without_loading_kernel_pool(tmp_path, monkeypatch):
    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    content = (
        b"KPL/LSK\n"
        b"\n\\begindata\n"
        b"DELTET/DELTA_T_A = 32.184\n"
        b"\\begintext\n"
    )
    registration = payload("test-lsk")
    registration["file_name"] = "test.tls"
    registration["kernel_type"] = "LSK"
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        assert client.post(
            "/api/v1/ephemeris/spice/kernels/test-lsk/artifact",
            files={"upload": ("test.tls", content, "text/plain")},
        ).status_code == 201
        inspected = client.post("/api/v1/ephemeris/spice/kernels/test-lsk/inspection")
        assert inspected.status_code == 201, inspected.text
        body = inspected.json()
        assert body["detected_architecture"] == "KPL"
        assert body["detected_kernel_type"] == "LSK"
        assert body["object_ids"] == []
        assert body["frame_class_ids"] == []
    finally:
        clear_overrides()


def test_inspection_rejects_artifact_changed_after_acquisition(tmp_path, monkeypatch):
    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    content = b"original uploaded bytes"
    registration = payload("tampered-artifact")
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        uploaded = client.post(
            "/api/v1/ephemeris/spice/kernels/tampered-artifact/artifact",
            files={"upload": ("kernel.tls", content, "application/octet-stream")},
        )
        assert uploaded.status_code == 201
        artifact_path = tmp_path / "artifacts" / uploaded.json()["storage_key"]
        artifact_path.write_bytes(b"changed after acquisition")

        inspected = client.post("/api/v1/ephemeris/spice/kernels/tampered-artifact/inspection")
        assert inspected.status_code == 422
        assert "no longer matches" in inspected.json()["detail"]
    finally:
        clear_overrides()

def test_naif_reference_lsk_converts_j2000_epoch_and_utc_round_trip():
    """Regression against the frozen NAIF naif0012 LSK data snapshot."""
    from pathlib import Path

    reference_lsk = Path(__file__).parent / "fixtures" / "naif0012_reference.tls"
    spice.kclear()
    try:
        spice.furnsh(str(reference_lsk))
        j2000_tdb_et = spice.str2et("2000 JAN 01 12:00:00 TDB")
        assert abs(j2000_tdb_et) < 1e-9

        utc_at_j2000 = spice.et2utc(0.0, "ISOC", 3)
        assert utc_at_j2000 == "2000-01-01T11:58:55.816"
        utc_round_trip_et = spice.str2et("2000 JAN 01 11:58:55.816 UTC")
        assert abs(utc_round_trip_et) < 5e-4  # ISOC output is rounded to milliseconds
    finally:
        spice.kclear()

def test_utc_to_et_conversion_requires_inspected_lsk_and_records_provenance(tmp_path, monkeypatch):
    from pathlib import Path

    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    fixture = Path(__file__).parent / "fixtures" / "naif0012_reference.tls"
    content = fixture.read_bytes()
    registration = payload("reference-lsk")
    registration["file_name"] = "naif0012_reference.tls"
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        not_ready = client.post(
            "/api/v1/ephemeris/spice/kernels/reference-lsk/time-conversions",
            json={"utc_time": "2000 JAN 01 11:58:55.816 UTC"},
        )
        assert not_ready.status_code == 409

        uploaded = client.post(
            "/api/v1/ephemeris/spice/kernels/reference-lsk/artifact",
            files={"upload": ("naif0012_reference.tls", content, "text/plain")},
        )
        assert uploaded.status_code == 201
        inspected = client.post("/api/v1/ephemeris/spice/kernels/reference-lsk/inspection")
        assert inspected.status_code == 201

        converted = client.post(
            "/api/v1/ephemeris/spice/kernels/reference-lsk/time-conversions",
            json={"utc_time": "2000 JAN 01 11:58:55.816 UTC"},
        )
        assert converted.status_code == 201, converted.text
        body = converted.json()
        assert abs(body["et_seconds"]) < 5e-4
        assert body["kernel_id"] == "reference-lsk"
        assert body["artifact_sha256"] == registration["sha256"]
        assert body["toolkit_version"] == "8.4.0"
        assert body["conversion_scope"] == "utc_to_et_using_single_registered_lsk"

        listed = client.get("/api/v1/ephemeris/spice/kernels/reference-lsk/time-conversions")
        assert listed.status_code == 200
        assert len(listed.json()) == 1
        retrieved = client.get(
            f"/api/v1/ephemeris/spice/kernels/reference-lsk/time-conversions/{body['conversion_id']}"
        )
        assert retrieved.status_code == 200
        assert retrieved.json()["et_seconds"] == body["et_seconds"]
    finally:
        clear_overrides()



def test_et_to_utc_conversion_records_lsk_provenance_and_precision(tmp_path, monkeypatch):
    from pathlib import Path

    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    fixture = Path(__file__).parent / "fixtures" / "naif0012_reference.tls"
    content = fixture.read_bytes()
    registration = payload("reference-lsk-et-to-utc")
    registration["file_name"] = "naif0012_reference.tls"
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        uploaded = client.post(
            "/api/v1/ephemeris/spice/kernels/reference-lsk-et-to-utc/artifact",
            files={"upload": ("naif0012_reference.tls", content, "text/plain")},
        )
        assert uploaded.status_code == 201
        assert client.post(
            "/api/v1/ephemeris/spice/kernels/reference-lsk-et-to-utc/inspection"
        ).status_code == 201

        converted = client.post(
            "/api/v1/ephemeris/spice/kernels/reference-lsk-et-to-utc/time-conversions/et-to-utc",
            json={"et_seconds": 0.0, "precision": 6},
        )
        assert converted.status_code == 201, converted.text
        body = converted.json()
        assert body["conversion_direction"] == "et_to_utc"
        assert body["input_et_seconds"] == 0.0
        assert body["input_utc"] is None
        assert body["et_seconds"] == 0.0
        assert body["normalized_utc"].startswith("2000-01-01T11:58:55.816")
        assert body["artifact_sha256"] == registration["sha256"]
        assert body["toolkit_version"] == "8.4.0"
    finally:
        clear_overrides()

def test_utc_to_et_rejects_missing_utc_suffix_and_non_lsk_registration(tmp_path):
    configure_store(tmp_path)
    non_lsk = payload("not-an-lsk")
    non_lsk["kernel_type"] = "SPK"
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=non_lsk).status_code == 201
        invalid_time = client.post(
            "/api/v1/ephemeris/spice/kernels/not-an-lsk/time-conversions",
            json={"utc_time": "2000-01-01T12:00:00"},
        )
        assert invalid_time.status_code == 422
        wrong_kernel = client.post(
            "/api/v1/ephemeris/spice/kernels/not-an-lsk/time-conversions",
            json={"utc_time": "2000-01-01T12:00:00 UTC"},
        )
        assert wrong_kernel.status_code == 409
    finally:
        clear_overrides()


def test_utc_to_et_rejects_lsk_artifact_tampering_after_inspection(tmp_path, monkeypatch):
    from pathlib import Path

    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    fixture = Path(__file__).parent / "fixtures" / "naif0012_reference.tls"
    content = fixture.read_bytes()
    registration = payload("tampered-lsk")
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        uploaded = client.post(
            "/api/v1/ephemeris/spice/kernels/tampered-lsk/artifact",
            files={"upload": ("naif0012_reference.tls", content, "text/plain")},
        )
        assert uploaded.status_code == 201
        assert client.post("/api/v1/ephemeris/spice/kernels/tampered-lsk/inspection").status_code == 201
        artifact_path = tmp_path / "artifacts" / uploaded.json()["storage_key"]
        artifact_path.write_bytes(b"tampered LSK")

        converted = client.post(
            "/api/v1/ephemeris/spice/kernels/tampered-lsk/time-conversions",
            json={"utc_time": "2000 JAN 01 11:58:55.816 UTC"},
        )
        assert converted.status_code == 422
        assert "no longer matches" in converted.json()["detail"]
    finally:
        clear_overrides()


def test_time_conversion_rejects_oversized_lsk_before_worker(tmp_path, monkeypatch):
    from pathlib import Path

    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    monkeypatch.setattr(spice_time_conversion, "MAX_LSK_CONVERSION_BYTES", 1)
    fixture = Path(__file__).parent / "fixtures" / "naif0012_reference.tls"
    content = fixture.read_bytes()
    registration = payload("oversized-lsk")
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        assert client.post(
            "/api/v1/ephemeris/spice/kernels/oversized-lsk/artifact",
            files={"upload": ("naif0012_reference.tls", content, "text/plain")},
        ).status_code == 201
        assert client.post(
            "/api/v1/ephemeris/spice/kernels/oversized-lsk/inspection"
        ).status_code == 201

        converted = client.post(
            "/api/v1/ephemeris/spice/kernels/oversized-lsk/time-conversions",
            json={"utc_time": "2000 JAN 01 11:58:55.816 UTC"},
        )
        assert converted.status_code == 422
        assert "conversion limit" in converted.json()["detail"]
    finally:
        clear_overrides()
