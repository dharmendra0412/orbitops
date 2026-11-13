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

    with pytest.raises(ArtifactSnapshotError, match="no longer matches"), verified_artifact_snapshot(
            source,
            expected_sha256=hashlib.sha256(b"original bytes").hexdigest(),
            max_bytes=1024,
            artifact_label="LSK",
        ):
            pytest.fail("unverified snapshot must never be yielded")


def test_verified_snapshot_enforces_size_limit(tmp_path):
    source = tmp_path / "kernel.tf"
    source.write_bytes(b"more than four bytes")

    with pytest.raises(ArtifactSnapshotError, match="4 byte limit"), verified_artifact_snapshot(
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

    with pytest.raises(ArtifactSnapshotError), verified_artifact_snapshot(
            link,
            expected_sha256=hashlib.sha256(b"kernel").hexdigest(),
            max_bytes=1024,
            artifact_label="LSK",
        ):
            pytest.fail("symlinked source must never be yielded")



def test_verified_snapshot_uses_the_open_descriptor_if_source_path_is_replaced(
    tmp_path, monkeypatch
):
    original = b"original bytes from the opened descriptor"
    replacement = b"replacement bytes at the same path"
    source = tmp_path / "kernel.tls"
    source.write_bytes(original)
    replacement_path = tmp_path / "replacement.tls"
    replacement_path.write_bytes(replacement)
    expected_digest = hashlib.sha256(original).hexdigest()

    real_open = os.open
    replaced = False

    def open_then_replace(path, flags, *args, **kwargs):
        nonlocal replaced
        descriptor = real_open(path, flags, *args, **kwargs)
        if path == source.name and kwargs.get("dir_fd") is not None and not replaced:
            os.replace(replacement_path, source)
            replaced = True
        return descriptor

    monkeypatch.setattr(os, "open", open_then_replace)

    with verified_artifact_snapshot(
        source,
        expected_sha256=expected_digest,
        max_bytes=1024,
        artifact_label="LSK",
    ) as (snapshot, actual_digest):
        assert replaced
        assert source.read_bytes() == replacement
        assert snapshot.read_bytes() == original
        assert actual_digest == expected_digest

    assert not snapshot.exists()



def test_verified_snapshot_pins_parent_directory_if_path_is_replaced_with_symlink(
    tmp_path, monkeypatch
):
    original = b"original artifact in pinned directory"
    replacement = b"external replacement must not be read"
    parent = tmp_path / "artifacts"
    parent.mkdir()
    source = parent / "kernel.bin"
    source.write_bytes(original)
    moved_parent = tmp_path / "pinned-original-directory"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "kernel.bin").write_bytes(replacement)
    expected_digest = hashlib.sha256(original).hexdigest()

    real_open = os.open
    swapped = False

    def replace_parent_before_final_open(path, flags, *args, **kwargs):
        nonlocal swapped
        if path == "kernel.bin" and kwargs.get("dir_fd") is not None and not swapped:
            parent.rename(moved_parent)
            parent.symlink_to(outside, target_is_directory=True)
            swapped = True
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", replace_parent_before_final_open)

    with verified_artifact_snapshot(
        source,
        expected_sha256=expected_digest,
        max_bytes=1024,
        artifact_label="LSK",
    ) as (snapshot, actual_digest):
        assert swapped
        assert snapshot.read_bytes() == original
        assert actual_digest == expected_digest

    assert (outside / "kernel.bin").read_bytes() == replacement


def test_verified_snapshot_rejects_symlinked_parent_directory(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    source = outside / "kernel.bin"
    source.write_bytes(b"kernel")
    link = tmp_path / "linked-directory"
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ArtifactSnapshotError), verified_artifact_snapshot(
        link / "kernel.bin",
        expected_sha256=hashlib.sha256(b"kernel").hexdigest(),
        max_bytes=1024,
        artifact_label="LSK",
    ):
        pytest.fail("a symlinked parent directory must never be followed")
