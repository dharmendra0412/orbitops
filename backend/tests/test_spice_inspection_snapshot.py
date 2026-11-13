"""Tests for immutable, digest-verified SPICE inspection snapshots."""

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from app.ephemeris import inspection


def _put_artifact(root: Path, content: bytes) -> tuple[Path, str]:
    digest = hashlib.sha256(content).hexdigest()
    artifact = root / "sha256" / digest[:2] / digest
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(content)
    return artifact, digest


def test_worker_receives_private_read_only_snapshot_of_verified_bytes(tmp_path, monkeypatch):
    content = b"KPL/LSK\n\\begindata\nDELTET/DELTA_T_A = 32.184\n"
    _artifact, digest = _put_artifact(tmp_path, content)
    observed = {}

    def fake_worker(command, **_kwargs):
        snapshot = Path(command[3])
        observed["snapshot_path"] = snapshot
        observed["snapshot_bytes"] = snapshot.read_bytes()
        observed["snapshot_mode"] = stat.S_IMODE(snapshot.stat().st_mode)
        observed["snapshot_parent_mode"] = stat.S_IMODE(snapshot.parent.stat().st_mode)
        observed["kernel_path"] = command[2]
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=json.dumps(
                {
                    "detected_architecture": "KPL",
                    "detected_kernel_type": "LSK",
                    "inspection_scope": "header",
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(inspection.subprocess, "run", fake_worker)

    record = inspection.inspect_artifact(
        kernel_id="snapshot-lsk",
        expected_type="LSK",
        expected_sha256=digest,
        storage_root=tmp_path,
    )

    assert observed["snapshot_bytes"] == content
    assert observed["snapshot_mode"] == 0o400
    assert observed["snapshot_parent_mode"] == 0o700
    assert not observed["snapshot_path"].is_relative_to(tmp_path)
    assert record.artifact_sha256 == digest
    assert record.detected_kernel_type == "LSK"
    assert not observed["snapshot_path"].exists()


def test_digest_mismatch_is_rejected_before_worker_starts(tmp_path, monkeypatch):
    artifact, digest = _put_artifact(tmp_path, b"original kernel bytes")
    artifact.write_bytes(b"changed kernel bytes")
    monkeypatch.setattr(
        inspection.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("worker must not run for an unverified snapshot"),
    )

    with pytest.raises(inspection.SpiceInspectionError, match="no longer matches"):
        inspection.inspect_artifact(
            kernel_id="changed-lsk",
            expected_type="LSK",
            expected_sha256=digest,
            storage_root=tmp_path,
        )


def test_inspection_rejects_non_regular_artifact(tmp_path, monkeypatch):
    artifact, digest = _put_artifact(tmp_path, b"kernel bytes")
    artifact.unlink()
    artifact.mkdir()
    monkeypatch.setattr(
        inspection.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("worker must not run for a directory"),
    )

    with pytest.raises(inspection.SpiceInspectionError, match="regular file"):
        inspection.inspect_artifact(
            kernel_id="directory-artifact",
            expected_type="LSK",
            expected_sha256=digest,
            storage_root=tmp_path,
        )
