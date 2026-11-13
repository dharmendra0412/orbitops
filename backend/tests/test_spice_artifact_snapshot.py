import hashlib
import os
import stat

import pytest

from app.ephemeris.artifact_snapshot import ArtifactSnapshotError, verified_artifact_snapshot


def test_verified_snapshot_is_private_read_only_and_removed_after_use(tmp_path):
    content = b"verified SPICE kernel bytes"
    source = tmp_path / "kernel.tls"
    source.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()

    with verified_artifact_snapshot(
        source,
        expected_sha256=digest,
        max_bytes=1024,
        artifact_label="LSK",
    ) as (snapshot, actual_digest):
        assert snapshot.read_bytes() == content
        assert actual_digest == digest
        assert stat.S_IMODE(snapshot.stat().st_mode) == 0o400
        assert stat.S_IMODE(snapshot.parent.stat().st_mode) == 0o700
        assert snapshot != source

    assert not snapshot.exists()


def test_verified_snapshot_rejects_digest_mismatch(tmp_path):
    source = tmp_path / "kernel.tls"
    source.write_bytes(b"changed bytes")

    with pytest.raises(ArtifactSnapshotError, match="no longer matches"):
        with verified_artifact_snapshot(
            source,
            expected_sha256=hashlib.sha256(b"original bytes").hexdigest(),
            max_bytes=1024,
            artifact_label="LSK",
        ):
            pytest.fail("unverified snapshot must never be yielded")


def test_verified_snapshot_enforces_size_limit(tmp_path):
    source = tmp_path / "kernel.tf"
    source.write_bytes(b"more than four bytes")

    with pytest.raises(ArtifactSnapshotError, match="4 byte limit"):
        with verified_artifact_snapshot(
            source,
            expected_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            max_bytes=4,
            artifact_label="FK",
        ):
            pytest.fail("oversized snapshot must never be yielded")


def test_verified_snapshot_rejects_final_symlink(tmp_path):
    source = tmp_path / "real-kernel.tls"
    source.write_bytes(b"kernel")
    link = tmp_path / "kernel.tls"
    link.symlink_to(source)

    with pytest.raises(ArtifactSnapshotError):
        with verified_artifact_snapshot(
            link,
            expected_sha256=hashlib.sha256(b"kernel").hexdigest(),
            max_bytes=1024,
            artifact_label="LSK",
        ):
            pytest.fail("symlinked source must never be yielded")
