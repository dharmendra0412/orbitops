"""Controlled invocation of the SPICE metadata inspection subprocess."""
import json  # noqa: I001
import os
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from app.ephemeris.artifact_snapshot import ArtifactSnapshotError, verified_artifact_snapshot
from app.ephemeris.kernels import SpiceKernelInspectionRecord


MAX_INSPECTION_SECONDS = 12
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
    """Inspect a private immutable snapshot of the acquired kernel artifact."""
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

    worker_path = Path(__file__).with_name("inspect_worker.py")
    backend_root = Path(__file__).resolve().parents[2]
    try:
        with verified_artifact_snapshot(
            resolved_path,
            expected_sha256=expected_sha256,
            max_bytes=MAX_INSPECTION_ARTIFACT_BYTES,
            artifact_label="kernel",
        ) as (snapshot_path, actual_sha256):
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
    except ArtifactSnapshotError as error:
        message = str(error)
        if "regular file" in message:
            raise SpiceInspectionError(
                "Content-addressed artifact must be a regular file"
            ) from error
        if "exceeds the" in message:
            raise SpiceInspectionError(
                "Kernel artifact exceeds the inspection size limit"
            ) from error
        if "no longer matches" in message:
            raise SpiceInspectionError(
                "Stored kernel artifact no longer matches its recorded SHA-256"
            ) from error
        raise SpiceInspectionError(
            "Unable to safely open or snapshot the kernel artifact"
        ) from error
    except SpiceInspectionError:
        raise
    except OSError as error:
        raise SpiceInspectionError(
            "Unable to safely open or snapshot the kernel artifact"
        ) from error
