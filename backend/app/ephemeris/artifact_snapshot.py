"""Private immutable snapshots for verified content-addressed SPICE artifacts."""
import hashlib  # noqa: I001
import os
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


HASH_CHUNK_BYTES = 1024 * 1024


def _open_source_without_symlink_components(source_path: Path) -> int:
    """Open an absolute path by walking pinned directory descriptors without links."""
    absolute_path = Path(os.path.abspath(source_path))
    components = absolute_path.parts
    if not components or components[0] != os.sep:
        raise OSError("Artifact source path must be absolute")

    directory_fd = os.open(os.sep, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        for component in components[1:-1]:
            next_fd = os.open(
                component,
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        return os.open(
            components[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
    finally:
        os.close(directory_fd)


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
        source_fd = _open_source_without_symlink_components(source_path)
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
