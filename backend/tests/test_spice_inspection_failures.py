"""Failure-path regression tests for the bounded SPICE inspection worker."""

import hashlib
import subprocess
from pathlib import Path

import pytest

from app.ephemeris import inspection


def _stored_artifact(tmp_path: Path, content: bytes = b"KPL/LSK\\n") -> tuple[Path, str]:
    digest = hashlib.sha256(content).hexdigest()
    artifact = tmp_path / "sha256" / digest[:2] / digest
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(content)
    return artifact, digest


def test_inspection_rejects_symlinked_content_addressed_artifact(tmp_path):
    artifact, digest = _stored_artifact(tmp_path)
    target = tmp_path / "outside-artifact"
    target.write_bytes(artifact.read_bytes())
    artifact.unlink()
    artifact.symlink_to(target)

    with pytest.raises(inspection.SpiceInspectionError, match="symbolic link"):
        inspection.inspect_artifact(
            kernel_id="test-lsk",
            expected_type="LSK",
            expected_sha256=digest,
            storage_root=tmp_path,
        )


def test_inspection_converts_worker_timeout_to_controlled_error(tmp_path, monkeypatch):
    _artifact, digest = _stored_artifact(tmp_path)

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="inspect_worker.py", timeout=12)

    monkeypatch.setattr(inspection.subprocess, "run", timeout)

    with pytest.raises(inspection.SpiceInspectionError, match="exceeded its time limit"):
        inspection.inspect_artifact(
            kernel_id="test-lsk",
            expected_type="LSK",
            expected_sha256=digest,
            storage_root=tmp_path,
        )


def test_inspection_rejects_invalid_worker_json(tmp_path, monkeypatch):
    _artifact, digest = _stored_artifact(tmp_path)
    monkeypatch.setattr(
        inspection.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["inspect_worker.py"], returncode=0, stdout="not-json", stderr=""
        ),
    )

    with pytest.raises(inspection.SpiceInspectionError, match="invalid result"):
        inspection.inspect_artifact(
            kernel_id="test-lsk",
            expected_type="LSK",
            expected_sha256=digest,
            storage_root=tmp_path,
        )


def test_inspection_reports_worker_parser_failure_without_traceback(tmp_path, monkeypatch):
    _artifact, digest = _stored_artifact(tmp_path)
    monkeypatch.setattr(
        inspection.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["inspect_worker.py"],
            returncode=2,
            stdout='{"error":"ValueError","detail":"malformed kernel"}',
            stderr="internal traceback must not be exposed",
        ),
    )

    with pytest.raises(inspection.SpiceInspectionError, match="malformed kernel"):
        inspection.inspect_artifact(
            kernel_id="test-lsk",
            expected_type="LSK",
            expected_sha256=digest,
            storage_root=tmp_path,
        )
