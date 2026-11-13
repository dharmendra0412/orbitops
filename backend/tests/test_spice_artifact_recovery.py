import hashlib
import os
from datetime import UTC, datetime

from app.ephemeris.kernels import SpiceKernelArtifactRecord, SpiceKernelRegistration
from app.storage.spice_artifact_recovery import audit_spice_artifact_storage
from app.storage.spice_kernels import SpiceKernelStore


def _registration(kernel_id: str, digest: str) -> SpiceKernelRegistration:
    return SpiceKernelRegistration.model_validate({
        "kernel_id": kernel_id,
        "file_name": "kernel.bsp",
        "kernel_type": "SPK",
        "source_url": "https://example.invalid/kernel.bsp",
        "provider": "Test provider",
        "release_or_version": "test",
        "sha256": digest,
        "coverage_start": None,
        "coverage_end": None,
        "time_system": "TDB",
        "reference_frames": ["J2000"],
        "target_names": [],
        "license_or_terms": "Test-only terms",
    })


def _write_artifact(root, content: bytes) -> tuple[str, str]:
    digest = hashlib.sha256(content).hexdigest()
    prefix = root / "sha256" / digest[:2]
    prefix.mkdir(parents=True, exist_ok=True)
    (prefix / digest).write_bytes(content)
    return digest, f"sha256/{digest[:2]}/{digest}"


def test_recovery_audit_distinguishes_referenced_and_orphan_artifacts(tmp_path):
    storage_root = tmp_path / "artifacts"
    storage_root.mkdir()
    (storage_root / ".staging").mkdir()
    store = SpiceKernelStore(tmp_path / "registry.sqlite3")

    referenced_bytes = b"registered content"
    referenced_digest, referenced_key = _write_artifact(storage_root, referenced_bytes)
    store.create(_registration("registered-kernel", referenced_digest))
    store.create_artifact(SpiceKernelArtifactRecord(
        kernel_id="registered-kernel",
        sha256=referenced_digest,
        size_bytes=len(referenced_bytes),
        storage_key=referenced_key,
        acquired_at=datetime.now(UTC),
    ))

    orphan_bytes = b"published before process interruption"
    orphan_digest, _ = _write_artifact(storage_root, orphan_bytes)

    report = audit_spice_artifact_storage(storage_root, store)

    classifications = {
        item["storage_key"]: item["classification"]
        for item in report["artifacts"]
    }
    assert classifications[referenced_key] == "referenced"
    assert classifications[f"sha256/{orphan_digest[:2]}/{orphan_digest}"] == "orphan_candidate"
    assert report["summary"]["referenced_artifacts"] == 1
    assert report["summary"]["orphan_candidates"] == 1
    assert all(item["deleted"] is False for item in report["artifacts"])


def test_recovery_audit_reports_digest_mismatch_without_modifying_file(tmp_path):
    storage_root = tmp_path / "artifacts"
    storage_root.mkdir()
    (storage_root / ".staging").mkdir()
    store = SpiceKernelStore(tmp_path / "registry.sqlite3")

    digest, _ = _write_artifact(storage_root, b"not the bytes named by this digest")
    artifact_path = storage_root / "sha256" / digest[:2] / digest
    artifact_path.write_bytes(b"tampered content")

    report = audit_spice_artifact_storage(storage_root, store)

    assert report["artifacts"][0]["classification"] == "integrity_mismatch"
    assert artifact_path.read_bytes() == b"tampered content"


def test_recovery_audit_marks_old_staging_files_for_review_only(tmp_path):
    storage_root = tmp_path / "artifacts"
    staging = storage_root / ".staging"
    staging.mkdir(parents=True)
    store = SpiceKernelStore(tmp_path / "registry.sqlite3")
    staging_file = staging / "interrupted.part"
    staging_file.write_bytes(b"partial upload")
    os.utime(staging_file, (100, 100))

    report = audit_spice_artifact_storage(
        storage_root,
        store,
        stale_after_seconds=60,
        now=1000,
    )

    assert report["staging"][0]["classification"] == "stale_candidate_review_only"
    assert report["staging"][0]["deleted"] is False
    assert staging_file.read_bytes() == b"partial upload"


def test_recovery_audit_does_not_follow_artifact_symlinks(tmp_path):
    storage_root = tmp_path / "artifacts"
    storage_root.mkdir()
    (storage_root / ".staging").mkdir()
    store = SpiceKernelStore(tmp_path / "registry.sqlite3")
    content = b"external file must remain untouched"
    digest = hashlib.sha256(content).hexdigest()
    prefix = storage_root / "sha256" / digest[:2]
    prefix.mkdir(parents=True)
    external = tmp_path / "external.bin"
    external.write_bytes(content)
    (prefix / digest).symlink_to(external)

    report = audit_spice_artifact_storage(storage_root, store)

    assert report["artifacts"][0]["classification"] == "unsafe_entry"
    assert external.read_bytes() == content
