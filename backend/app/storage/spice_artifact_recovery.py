"""Read-only crash-recovery audit for content-addressed SPICE artifact storage."""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import stat
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.storage.spice_kernels import SpiceKernelStore

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PREFIX_RE = re.compile(r"^[0-9a-f]{2}$")
_CHUNK_BYTES = 1024 * 1024


def audit_spice_artifact_storage(
    storage_root: str | Path,
    store: SpiceKernelStore,
    *,
    stale_after_seconds: int = 3600,
    now: float | None = None,
) -> dict[str, object]:
    """Return a read-only storage audit; this function never deletes or modifies files.

    Digest directories are locked while their files are compared with the database.
    Upload publication holds the same lock through its SQLite commit, so an in-flight
    publication cannot be reported as an orphan. Staging files cannot be locked by
    digest before upload completion and are therefore reported for manual review only.
    """
    if stale_after_seconds < 0:
        raise ValueError("stale_after_seconds must be non-negative")
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise RuntimeError("SPICE storage audit requires POSIX no-follow directory support")

    current_time = time.time() if now is None else now
    root_fd = os.open(
        Path(storage_root),
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )
    report: dict[str, object] = {
        "mode": "read_only",
        "storage_root": str(storage_root),
        "staging": [],
        "artifacts": [],
        "summary": {
            "staging_entries": 0,
            "stale_staging_review": 0,
            "referenced_artifacts": 0,
            "orphan_candidates": 0,
            "integrity_mismatches": 0,
            "unsafe_entries": 0,
        },
    }
    try:
        staging_fd = _open_child_directory(root_fd, ".staging")
        if staging_fd is not None:
            try:
                for name in sorted(os.listdir(staging_fd)):
                    try:
                        metadata = os.stat(name, dir_fd=staging_fd, follow_symlinks=False)
                    except FileNotFoundError:
                        # An uploader may finish and unlink its staging name while
                        # this directory snapshot is being enumerated.
                        continue
                    age = max(0.0, current_time - metadata.st_mtime)
                    regular = stat.S_ISREG(metadata.st_mode)
                    item = {
                        "name": name,
                        "size_bytes": metadata.st_size if regular else None,
                        "age_seconds": int(age),
                        "classification": (
                            "stale_candidate_review_only"
                            if regular and age >= stale_after_seconds
                            else "recent_or_active_unknown" if regular else "unsafe_entry"
                        ),
                        "deleted": False,
                    }
                    report["staging"].append(item)
                    summary = report["summary"]
                    summary["staging_entries"] += 1
                    if item["classification"] == "stale_candidate_review_only":
                        summary["stale_staging_review"] += 1
                    if item["classification"] == "unsafe_entry":
                        summary["unsafe_entries"] += 1
            finally:
                os.close(staging_fd)

        sha_root_fd = _open_child_directory(root_fd, "sha256")
        if sha_root_fd is not None:
            try:
                for prefix in sorted(os.listdir(sha_root_fd)):
                    if not _PREFIX_RE.fullmatch(prefix):
                        report["artifacts"].append({
                            "name": prefix,
                            "classification": "unsafe_or_malformed_prefix",
                            "deleted": False,
                        })
                        report["summary"]["unsafe_entries"] += 1
                        continue
                    prefix_fd = _open_child_directory(sha_root_fd, prefix)
                    if prefix_fd is None:
                        continue
                    try:
                        fcntl.flock(prefix_fd, fcntl.LOCK_EX)
                        # Refresh references only after acquiring the same lock used
                        # by publishers, and immediately before classifying this prefix.
                        references = {
                            item.storage_key: item
                            for item in store.list_artifacts()
                            if item.storage_key.startswith(f"sha256/{prefix}/")
                        }
                        for digest_name in sorted(os.listdir(prefix_fd)):
                            if not _SHA256_RE.fullmatch(digest_name) or not digest_name.startswith(prefix):
                                report["artifacts"].append({
                                    "name": f"{prefix}/{digest_name}",
                                    "classification": "unsafe_or_malformed_name",
                                    "deleted": False,
                                })
                                report["summary"]["unsafe_entries"] += 1
                                continue
                            item = _inspect_digest_file(
                                prefix_fd,
                                digest_name,
                                f"sha256/{prefix}/{digest_name}",
                                references,
                            )
                            report["artifacts"].append(item)
                            summary = report["summary"]
                            if item["classification"] == "referenced":
                                summary["referenced_artifacts"] += 1
                            elif item["classification"] == "orphan_candidate":
                                summary["orphan_candidates"] += 1
                            elif item["classification"] == "unsafe_entry":
                                summary["unsafe_entries"] += 1
                            else:
                                summary["integrity_mismatches"] += 1
                    finally:
                        try:
                            fcntl.flock(prefix_fd, fcntl.LOCK_UN)
                        finally:
                            os.close(prefix_fd)
            finally:
                os.close(sha_root_fd)
    finally:
        os.close(root_fd)
    return report


def _open_child_directory(parent_fd: int, name: str) -> int | None:
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
    except FileNotFoundError:
        return None
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        raise OSError(f"SPICE storage component is not a directory: {name}")
    return descriptor


def _inspect_digest_file(
    prefix_fd: int,
    name: str,
    storage_key: str,
    references: dict[str, object],
) -> dict[str, object]:
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=prefix_fd)
    except OSError:
        return {"storage_key": storage_key, "classification": "unsafe_entry", "deleted": False}
    with os.fdopen(descriptor, "rb") as artifact:
        metadata = os.fstat(artifact.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            return {"storage_key": storage_key, "classification": "unsafe_entry", "deleted": False}
        digest = hashlib.sha256()
        size_bytes = 0
        while chunk := artifact.read(_CHUNK_BYTES):
            digest.update(chunk)
            size_bytes += len(chunk)

    reference = references.get(storage_key)
    if reference is None:
        classification = "orphan_candidate" if digest.hexdigest() == name else "integrity_mismatch"
    else:
        classification = (
            "referenced"
            if reference.sha256 == name and reference.size_bytes == size_bytes
            else "integrity_mismatch"
        )
    return {
        "storage_key": storage_key,
        "size_bytes": size_bytes,
        "sha256_matches_name": digest.hexdigest() == name,
        "classification": classification,
        "deleted": False,
    }
