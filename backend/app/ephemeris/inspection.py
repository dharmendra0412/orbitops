"""Controlled invocation of the SPICE metadata inspection subprocess."""
import hashlib  # noqa: I001
import json
import os
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from app.ephemeris.kernels import SpiceKernelInspectionRecord


MAX_INSPECTION_SECONDS = 12
HASH_CHUNK_BYTES = 1024 * 1024
MAX_INSPECTION_ARTIFACT_BYTES = 1024 * 1024 * 1024


class SpiceInspectionError(Exception):
    """Raised when a stored artifact cannot be safely inspected."""


def inspect_artifact(
    *,
    kernel_id: str,
    expected_type: str,
    expected_sha256: str,
    storage_root: Path,
) -> SpiceKernelInspectionRecord:
    """Hash a no-follow source descriptor and inspect a private immutable snapshot.

    The worker never opens the mutable content-addressed path. Bytes are copied
    from one opened regular-file descriptor into a private temporary directory
    while hashing; CSPICE then inspects that exact verified snapshot.
    """
    root = storage_root.resolve()
    artifact_path = root / "sha256" / expected_sha256[:2] / expected_sha256
    if artifact_path.is_symlink():
        raise SpiceInspectionError("Content-addressed artifact must not be a symbolic link")

    try:
        resolved_path = artifact_path.resolve(strict=True)
    except FileNotFoundError as error:
        raise SpiceInspectionError("Registered kernel artifact is missing from storage") from error

    if not resolved_path.is_relative_to(root):
        raise SpiceInspectionError("Kernel artifact path is outside the configured storage root")

    source_fd = None
    try:
        source_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        source_fd = os.open(resolved_path, source_flags)
        if not stat.S_ISREG(os.fstat(source_fd).st_mode):
            raise SpiceInspectionError("Content-addressed artifact must be a regular file")

        with tempfile.TemporaryDirectory(prefix="orbitops-spice-inspect-") as temporary_dir:
            snapshot_path = Path(temporary_dir) / "kernel-artifact"
            digest = hashlib.sha256()
            size_bytes = 0
            with os.fdopen(source_fd, "rb") as source_file:
                source_fd = None
                with snapshot_path.open("xb") as snapshot:
                    while chunk := source_file.read(HASH_CHUNK_BYTES):
                        size_bytes += len(chunk)
                        if size_bytes > MAX_INSPECTION_ARTIFACT_BYTES:
                            raise SpiceInspectionError(
                                "Kernel artifact exceeds the inspection size limit"
                            )
                        digest.update(chunk)
                        snapshot.write(chunk)
                    snapshot.flush()
                    os.fsync(snapshot.fileno())

            actual_sha256 = digest.hexdigest()
            if actual_sha256 != expected_sha256:
                raise SpiceInspectionError(
                    "Stored kernel artifact no longer matches its recorded SHA-256"
                )

            snapshot_path.chmod(0o400)
            worker_path = Path(__file__).with_name("inspect_worker.py")
            backend_root = Path(__file__).resolve().parents[2]
            try:
                completed = subprocess.run(
                    [sys.executable, "-I", str(worker_path), str(snapshot_path), expected_type],
                    cwd=backend_root,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=MAX_INSPECTION_SECONDS,
                    env={
                        "PATH": os.environ.get("PATH", ""),
                        "PYTHONDONTWRITEBYTECODE": "1",
                        **{
                            key: os.environ[key]
                            for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")
                            if key in os.environ
                        },
                    },
                )
            except subprocess.TimeoutExpired as error:
                raise SpiceInspectionError("SPICE inspection exceeded its time limit") from error
            except OSError as error:
                raise SpiceInspectionError("Unable to start the SPICE inspection worker") from error

            if completed.returncode != 0:
                try:
                    detail = json.loads(completed.stdout).get(
                        "detail", "CSPICE rejected the artifact"
                    )
                except (json.JSONDecodeError, AttributeError):
                    detail = "CSPICE inspection worker failed"
                raise SpiceInspectionError(str(detail)[:500])

            try:
                result = json.loads(completed.stdout)
                try:
                    toolkit_version = version("spiceypy")
                except PackageNotFoundError as error:
                    raise SpiceInspectionError(
                        "SPICE inspection is unavailable; install the pinned spice optional dependency"
                    ) from error

                return SpiceKernelInspectionRecord(
                    kernel_id=kernel_id,
                    artifact_sha256=actual_sha256,
                    toolkit_version=toolkit_version,
                    inspected_at=datetime.now(UTC),
                    **result,
                )
            except SpiceInspectionError:
                raise
            except (json.JSONDecodeError, TypeError, ValueError, KeyError) as error:
                raise SpiceInspectionError(
                    "SPICE inspection worker returned an invalid result"
                ) from error
    except SpiceInspectionError:
        raise
    except OSError as error:
        raise SpiceInspectionError("Unable to safely open or snapshot the kernel artifact") from error
    finally:
        if source_fd is not None:
            os.close(source_fd)
