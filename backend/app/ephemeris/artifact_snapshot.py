"""Private immutable snapshots for verified content-addressed SPICE artifacts."""
import hashlib  # noqa: I001
import os
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


HASH_CHUNK_BYTES = 1024 * 1024


class ArtifactSnapshotError(Exception):
    """Raised when an artifact cannot be safely copied into a verified snapshot."""


@contextmanager
def verified_artifact_snapshot(
    source_path: Path,
    *,
    expected_sha256: str,
    max_bytes: int,
    artifact_label: str,
) -> Iterator[tuple[Path, str]]:
    """Yield a private read-only copy made from the same descriptor that was hashed.

    The source is opened without following a final symlink, checked as a regular
    file, and copied while hashing. The worker can therefore consume only the
    exact bytes whose digest was verified, not a mutable storage path.
    """
    source_fd: int | None = None
    try:
        source_fd = os.open(
            source_path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
        if not stat.S_ISREG(os.fstat(source_fd).st_mode):
            raise ArtifactSnapshotError(
                f"Content-addressed {artifact_label} artifact must be a regular file"
            )

        with tempfile.TemporaryDirectory(prefix="orbitops-spice-snapshot-") as directory:
            snapshot_path = Path(directory) / "verified-artifact"
            digest = hashlib.sha256()
            size_bytes = 0
            with os.fdopen(source_fd, "rb") as source:
                source_fd = None
                with snapshot_path.open("xb") as snapshot:
                    while chunk := source.read(HASH_CHUNK_BYTES):
                        size_bytes += len(chunk)
                        if size_bytes > max_bytes:
                            raise ArtifactSnapshotError(
                                f"{artifact_label} artifact exceeds the {max_bytes} byte limit"
                            )
                        digest.update(chunk)
                        snapshot.write(chunk)
                    snapshot.flush()
                    os.fsync(snapshot.fileno())

            actual_sha256 = digest.hexdigest()
            if actual_sha256 != expected_sha256:
                raise ArtifactSnapshotError(
                    f"Stored {artifact_label} artifact no longer matches its recorded SHA-256"
                )

            snapshot_path.chmod(0o400)
            yield snapshot_path, actual_sha256
    except ArtifactSnapshotError:
        raise
    except OSError as error:
        raise ArtifactSnapshotError(
            f"Unable to safely open or snapshot the {artifact_label} artifact"
        ) from error
    finally:
        if source_fd is not None:
            os.close(source_fd)
