import hashlib
import os
import sqlite3
from datetime import UTC, datetime

import pytest
import spiceypy as spice
from fastapi.testclient import TestClient

import app.ephemeris.routes as spice_routes
import app.ephemeris.time_conversion as spice_time_conversion
from app.ephemeris.kernels import SpiceKernelArtifactRecord, SpiceKernelInspectionRecord
from app.ephemeris.routes import get_spice_kernel_store
from app.main import app
from app.storage.spice_kernels import SpiceKernelAlreadyExistsError, SpiceKernelStore

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
        artifact_path.chmod(0o600)
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
        artifact_path.chmod(0o600)
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



def test_fixed_fk_position_and_state_transformations_match_reference_rotation(tmp_path, monkeypatch):
    from pathlib import Path

    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    fixture = Path(__file__).parent / "fixtures" / "orbitops_fixed_frame_reference.tf"
    content = fixture.read_bytes()
    registration = payload("fixed-frame-reference")
    registration["file_name"] = "orbitops_fixed_frame_reference.tf"
    registration["kernel_type"] = "FK"
    registration["source_url"] = "https://example.invalid/orbitops_fixed_frame_reference.tf"
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        uploaded = client.post(
            "/api/v1/ephemeris/spice/kernels/fixed-frame-reference/artifact",
            files={"upload": ("orbitops_fixed_frame_reference.tf", content, "text/plain")},
        )
        assert uploaded.status_code == 201
        inspected = client.post(
            "/api/v1/ephemeris/spice/kernels/fixed-frame-reference/inspection"
        )
        assert inspected.status_code == 201
        assert inspected.json()["detected_architecture"] == "KPL"
        assert inspected.json()["detected_kernel_type"] == "FK"

        position = client.post(
            "/api/v1/ephemeris/spice/kernels/fixed-frame-reference/frame-transformations",
            json={
                "from_frame": "J2000",
                "to_frame": "ORBITOPS_TEST_FIXED",
                "et_seconds": 0.0,
                "transform_type": "position",
                "vector": [1.0, 0.0, 0.0],
            },
        )
        assert position.status_code == 201, position.text
        position_body = position.json()
        assert position_body["artifact_sha256"] == registration["sha256"]
        assert position_body["transform_type"] == "position"
        assert position_body["matrix"] == [
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        assert position_body["output_vector"] == [0.0, -1.0, 0.0]

        state = client.post(
            "/api/v1/ephemeris/spice/kernels/fixed-frame-reference/frame-transformations",
            json={
                "from_frame": "J2000",
                "to_frame": "ORBITOPS_TEST_FIXED",
                "et_seconds": 123.0,
                "transform_type": "state",
                "vector": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            },
        )
        assert state.status_code == 201, state.text
        state_body = state.json()
        assert len(state_body["matrix"]) == 6
        assert all(len(row) == 6 for row in state_body["matrix"])
        assert state_body["output_vector"] == [0.0, -1.0, 0.0, 1.0, 0.0, 0.0]

        history = client.get(
            "/api/v1/ephemeris/spice/kernels/fixed-frame-reference/frame-transformations"
        )
        assert history.status_code == 200
        assert len(history.json()) == 2
        retrieved = client.get(
            "/api/v1/ephemeris/spice/kernels/fixed-frame-reference/frame-transformations/"
            + position_body["transformation_id"]
        )
        assert retrieved.status_code == 200
        assert retrieved.json()["matrix"] == position_body["matrix"]
    finally:
        clear_overrides()


def test_frame_transform_rejects_unknown_frame_and_non_fk_kernel(tmp_path, monkeypatch):
    from pathlib import Path

    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    fixture = Path(__file__).parent / "fixtures" / "orbitops_fixed_frame_reference.tf"
    content = fixture.read_bytes()
    registration = payload("bad-frame-request")
    registration["file_name"] = "orbitops_fixed_frame_reference.tf"
    registration["kernel_type"] = "FK"
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        assert client.post(
            "/api/v1/ephemeris/spice/kernels/bad-frame-request/artifact",
            files={"upload": ("orbitops_fixed_frame_reference.tf", content, "text/plain")},
        ).status_code == 201
        assert client.post(
            "/api/v1/ephemeris/spice/kernels/bad-frame-request/inspection"
        ).status_code == 201

        unknown = client.post(
            "/api/v1/ephemeris/spice/kernels/bad-frame-request/frame-transformations",
            json={
                "from_frame": "J2000",
                "to_frame": "FRAME_THAT_DOES_NOT_EXIST",
                "et_seconds": 0.0,
            },
        )
        assert unknown.status_code == 422
        invalid_vector = client.post(
            "/api/v1/ephemeris/spice/kernels/bad-frame-request/frame-transformations",
            json={
                "from_frame": "J2000",
                "to_frame": "ORBITOPS_TEST_FIXED",
                "et_seconds": 0.0,
                "transform_type": "position",
                "vector": [1.0, 2.0],
            },
        )
        assert invalid_vector.status_code == 422

        not_fk = payload("not-a-frame-kernel")
        not_fk["kernel_type"] = "SPK"
        assert client.post("/api/v1/ephemeris/spice/kernels", json=not_fk).status_code == 201
        rejected = client.post(
            "/api/v1/ephemeris/spice/kernels/not-a-frame-kernel/frame-transformations",
            json={"from_frame": "J2000", "to_frame": "ORBITOPS_TEST_FIXED", "et_seconds": 0.0},
        )
        assert rejected.status_code == 409
    finally:
        clear_overrides()


def test_frame_transform_rejects_fk_artifact_tampering(tmp_path, monkeypatch):
    from pathlib import Path

    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", tmp_path / "artifacts")
    fixture = Path(__file__).parent / "fixtures" / "orbitops_fixed_frame_reference.tf"
    content = fixture.read_bytes()
    registration = payload("tampered-frame-fk")
    registration["file_name"] = "orbitops_fixed_frame_reference.tf"
    registration["kernel_type"] = "FK"
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post("/api/v1/ephemeris/spice/kernels", json=registration).status_code == 201
        uploaded = client.post(
            "/api/v1/ephemeris/spice/kernels/tampered-frame-fk/artifact",
            files={"upload": ("orbitops_fixed_frame_reference.tf", content, "text/plain")},
        )
        assert uploaded.status_code == 201
        assert client.post(
            "/api/v1/ephemeris/spice/kernels/tampered-frame-fk/inspection"
        ).status_code == 201
        artifact_path = tmp_path / "artifacts" / uploaded.json()["storage_key"]
        artifact_path.chmod(0o600)
        artifact_path.write_bytes(b"tampered FK")

        response = client.post(
            "/api/v1/ephemeris/spice/kernels/tampered-frame-fk/frame-transformations",
            json={"from_frame": "J2000", "to_frame": "ORBITOPS_TEST_FIXED", "et_seconds": 0.0},
        )
        assert response.status_code == 422
        assert "no longer matches" in response.json()["detail"]
    finally:
        clear_overrides()



def test_artifact_upload_rejects_preexisting_symlink_at_content_addressed_path(
    tmp_path, monkeypatch
):
    configure_store(tmp_path)
    storage_root = tmp_path / "artifacts"
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", storage_root)
    content = b"valid bytes whose digest is already known"
    digest = hashlib.sha256(content).hexdigest()
    registration = payload("preexisting-symlink")
    registration["sha256"] = digest
    try:
        assert client.post(
            "/api/v1/ephemeris/spice/kernels", json=registration
        ).status_code == 201
        artifact_path = storage_root / "sha256" / digest[:2] / digest
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        external_target = tmp_path / "external-target.bin"
        external_target.write_bytes(content)
        artifact_path.symlink_to(external_target)

        response = client.post(
            "/api/v1/ephemeris/spice/kernels/preexisting-symlink/artifact",
            files={"upload": ("kernel.bin", content, "application/octet-stream")},
        )

        assert response.status_code == 500
        assert "safely publish or verify" in response.json()["detail"]
        assert external_target.read_bytes() == content
        assert client.get(
            "/api/v1/ephemeris/spice/kernels/preexisting-symlink/artifact"
        ).status_code == 404
    finally:
        clear_overrides()


def test_artifact_upload_reuses_only_matching_regular_content_addressed_file(
    tmp_path, monkeypatch
):
    configure_store(tmp_path)
    storage_root = tmp_path / "artifacts"
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", storage_root)
    content = b"identical content can safely be deduplicated"
    digest = hashlib.sha256(content).hexdigest()
    registration = payload("existing-valid-artifact")
    registration["sha256"] = digest
    try:
        assert client.post(
            "/api/v1/ephemeris/spice/kernels", json=registration
        ).status_code == 201
        artifact_path = storage_root / "sha256" / digest[:2] / digest
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(content)
        artifact_path.chmod(0o600)

        response = client.post(
            "/api/v1/ephemeris/spice/kernels/existing-valid-artifact/artifact",
            files={"upload": ("kernel.bin", content, "application/octet-stream")},
        )

        assert response.status_code == 201, response.text
        assert artifact_path.read_bytes() == content
        assert artifact_path.stat().st_mode & 0o777 == 0o444
    finally:
        clear_overrides()



def test_artifact_upload_rejects_symlinked_staging_directory(tmp_path, monkeypatch):
    configure_store(tmp_path)
    storage_root = tmp_path / "artifacts"
    storage_root.mkdir()
    outside = tmp_path / "outside-staging"
    outside.mkdir()
    (storage_root / ".staging").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", storage_root)
    content = b"must not be staged through a symlink"
    registration = payload("symlinked-staging")
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post(
            "/api/v1/ephemeris/spice/kernels", json=registration
        ).status_code == 201
        response = client.post(
            "/api/v1/ephemeris/spice/kernels/symlinked-staging/artifact",
            files={"upload": ("kernel.bin", content, "application/octet-stream")},
        )
        assert response.status_code == 500
        assert "storage directories" in response.json()["detail"]
        assert list(outside.iterdir()) == []
    finally:
        clear_overrides()


def test_artifact_upload_rejects_symlinked_digest_directory(tmp_path, monkeypatch):
    configure_store(tmp_path)
    storage_root = tmp_path / "artifacts"
    storage_root.mkdir()
    outside = tmp_path / "outside-digests"
    outside.mkdir()
    (storage_root / "sha256").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", storage_root)
    content = b"must not be published through a symlink"
    registration = payload("symlinked-digest-directory")
    registration["sha256"] = hashlib.sha256(content).hexdigest()
    try:
        assert client.post(
            "/api/v1/ephemeris/spice/kernels", json=registration
        ).status_code == 201
        response = client.post(
            "/api/v1/ephemeris/spice/kernels/symlinked-digest-directory/artifact",
            files={"upload": ("kernel.bin", content, "application/octet-stream")},
        )
        assert response.status_code == 500
        assert "storage directories" in response.json()["detail"]
        assert list(outside.iterdir()) == []
    finally:
        clear_overrides()


def test_artifact_upload_rejects_hardlinked_existing_content_without_chmod_side_effect(
    tmp_path, monkeypatch
):
    configure_store(tmp_path)
    storage_root = tmp_path / "artifacts"
    monkeypatch.setattr(spice_routes.settings, "spice_kernel_storage_path", storage_root)
    content = b"same content but external hardlink must not be modified"
    digest = hashlib.sha256(content).hexdigest()
    registration = payload("hardlinked-existing-artifact")
    registration["sha256"] = digest
    try:
        assert client.post(
            "/api/v1/ephemeris/spice/kernels", json=registration
        ).status_code == 201
        artifact_path = storage_root / "sha256" / digest[:2] / digest
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        external_alias = tmp_path / "external-alias.bin"
        external_alias.write_bytes(content)
        external_alias.chmod(0o600)
        os.link(external_alias, artifact_path)

        response = client.post(
            "/api/v1/ephemeris/spice/kernels/hardlinked-existing-artifact/artifact",
            files={"upload": ("kernel.bin", content, "application/octet-stream")},
        )

        assert response.status_code == 500
        assert "singly linked regular file" in response.json()["detail"]
        assert external_alias.stat().st_mode & 0o777 == 0o600
        assert external_alias.read_bytes() == content
    finally:
        clear_overrides()



def test_concurrent_artifact_publication_serializes_deduplication(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    content = b"concurrent publication must leave one immutable artifact"
    digest = hashlib.sha256(content).hexdigest()
    staging = tmp_path / ".staging"
    artifact_directory = tmp_path / "sha256" / digest[:2]
    staging.mkdir()
    artifact_directory.mkdir(parents=True)
    temporary_names = ("first.part", "second.part")
    for name in temporary_names:
        (staging / name).write_bytes(content)

    def publish(name):
        staging_fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY)
        artifact_fd = os.open(artifact_directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            spice_routes._publish_content_addressed_artifact(
                name,
                staging_fd,
                artifact_fd,
                expected_sha256=digest,
                expected_size=len(content),
            )
        finally:
            os.close(staging_fd)
            os.close(artifact_fd)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(publish, name) for name in temporary_names]
        for future in futures:
            future.result()

    artifact = artifact_directory / digest
    assert artifact.read_bytes() == content
    assert artifact.stat().st_nlink == 1
    assert artifact.stat().st_mode & 0o777 == 0o444
    assert list(staging.iterdir()) == []



def test_spice_registry_enforces_foreign_keys_on_every_connection(tmp_path):
    store = SpiceKernelStore(tmp_path / "spice-kernels.sqlite3")

    with store._connection() as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    invalid_inserts = [
        (
            """INSERT INTO spice_kernel_artifacts
               (kernel_id, payload_json, acquired_at) VALUES (?, ?, ?)""",
            ("missing-registration", "{}", "2026-01-01T00:00:00+00:00"),
        ),
        (
            """INSERT INTO spice_kernel_inspections
               (kernel_id, payload_json, inspected_at) VALUES (?, ?, ?)""",
            ("missing-artifact", "{}", "2026-01-01T00:00:00+00:00"),
        ),
        (
            """INSERT INTO spice_time_conversions
               (conversion_id, kernel_id, payload_json, converted_at)
               VALUES (?, ?, ?, ?)""",
            ("conversion-1", "missing-inspection", "{}", "2026-01-01T00:00:00+00:00"),
        ),
        (
            """INSERT INTO spice_frame_transformations
               (transformation_id, kernel_id, payload_json, transformed_at)
               VALUES (?, ?, ?, ?)""",
            ("transform-1", "missing-inspection", "{}", "2026-01-01T00:00:00+00:00"),
        ),
    ]

    for statement, parameters in invalid_inserts:
        with (
            pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"),
            store._connection() as connection,
        ):
            connection.execute(statement, parameters)



def test_spice_registry_startup_detects_preexisting_foreign_key_violations(tmp_path):
    database_path = tmp_path / "spice-kernels.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """CREATE TABLE spice_kernel_registrations (
                kernel_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                registered_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE spice_kernel_artifacts (
                kernel_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                acquired_at TEXT NOT NULL,
                FOREIGN KEY(kernel_id) REFERENCES spice_kernel_registrations(kernel_id)
            )"""
        )
        # Simulate rows written by an older application connection where
        # SQLite's per-connection foreign-key enforcement was left disabled.
        connection.execute(
            """INSERT INTO spice_kernel_artifacts
               (kernel_id, payload_json, acquired_at) VALUES (?, ?, ?)""",
            ("orphan-artifact", "{}", "2026-01-01T00:00:00+00:00"),
        )

    with pytest.raises(RuntimeError, match="existing foreign-key violations"):
        SpiceKernelStore(database_path)



def test_spice_store_does_not_misclassify_foreign_key_failures_as_duplicates(tmp_path):
    store = SpiceKernelStore(tmp_path / "spice-kernels.sqlite3")
    now = datetime.now(UTC)

    artifact = SpiceKernelArtifactRecord(
        kernel_id="missing-registration",
        sha256="a" * 64,
        size_bytes=1,
        storage_key="sha256/aa/" + "a" * 64,
        acquired_at=now,
    )
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
        store.create_artifact(artifact)

    inspection = SpiceKernelInspectionRecord(
        kernel_id="missing-artifact",
        artifact_sha256="b" * 64,
        toolkit_version="8.4.0",
        detected_architecture="KPL",
        detected_kernel_type="LSK",
        inspection_scope="regression-test",
        inspected_at=now,
    )
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
        store.create_inspection(inspection)


def test_spice_store_still_maps_duplicate_registry_records_to_conflict(tmp_path):
    from app.ephemeris.kernels import SpiceKernelRegistration

    store = SpiceKernelStore(tmp_path / "spice-kernels.sqlite3")
    registration = SpiceKernelRegistration.model_validate(payload())
    store.create(registration)

    with pytest.raises(SpiceKernelAlreadyExistsError):
        store.create(registration)



def test_artifact_upload_reports_unsupported_secure_storage_runtime(tmp_path, monkeypatch):
    store = configure_store(tmp_path)
    monkeypatch.setattr(spice_routes, "_supports_secure_artifact_storage", lambda: False)
    try:
        response = client.post(
            "/api/v1/ephemeris/spice/kernels/missing/artifact",
            files={"upload": ("kernel.bin", b"not-written", "application/octet-stream")},
        )
        assert response.status_code == 501
        assert "requires a POSIX runtime" in response.json()["detail"]
        assert not (tmp_path / "artifacts").exists()
        assert store.get("missing") is None
    finally:
        clear_overrides()



def test_all_spice_artifact_consumers_reject_unsupported_storage_runtime(tmp_path, monkeypatch):
    configure_store(tmp_path)
    monkeypatch.setattr(spice_routes, "_supports_secure_artifact_storage", lambda: False)
    requests = [
        (
            "post",
            "/api/v1/ephemeris/spice/kernels/missing/inspection",
            {},
        ),
        (
            "post",
            "/api/v1/ephemeris/spice/kernels/missing/time-conversions",
            {"json": {"utc_time": "2000 JAN 01 11:58:55.816 UTC"}},
        ),
        (
            "post",
            "/api/v1/ephemeris/spice/kernels/missing/time-conversions/et-to-utc",
            {"json": {"et_seconds": 0.0, "precision": 3}},
        ),
        (
            "post",
            "/api/v1/ephemeris/spice/kernels/missing/frame-transformations",
            {
                "json": {
                    "from_frame": "J2000",
                    "to_frame": "IAU_EARTH",
                    "et_seconds": 0.0,
                    "vector": [1.0, 0.0, 0.0],
                }
            },
        ),
    ]
    try:
        for method, path, kwargs in requests:
            response = getattr(client, method)(path, **kwargs)
            assert response.status_code == 501, (path, response.text)
            assert "require a POSIX runtime" in response.json()["detail"]
    finally:
        clear_overrides()
