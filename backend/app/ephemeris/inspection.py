"""Controlled invocation of the SPICE metadata inspection subprocess."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from app.ephemeris.kernels import SpiceKernelInspectionRecord


MAX_INSPECTION_SECONDS = 12
HASH_CHUNK_BYTES = 1024 * 1024


class SpiceInspectionError(Exception):
    """Raised when a stored artifact cannot be safely inspected."""


def inspect_artifact(
    *,
    kernel_id: str,
    expected_type: str,
    expected_sha256: str,
    storage_root: Path,
) -> SpiceKernelInspectionRecord:
    """Re-hash a content-addressed artifact and inspect it in a bounded child process."""
    root = storage_root.resolve()
    artifact_path = root / "sha256" / expected_sha256[:2] / expected_sha256
    if artifact_path.is_symlink():
        raise SpiceInspectionError("Content-addressed artifact must not be a symbolic link")

    try:
        resolved_path = artifact_path.resolve(strict=True)
    except FileNotFoundError as error:
        raise SpiceInspectionError("Registered kernel artifact is missing from storage") from error

    if not resolved_path.is_relative_to(root) or not resolved_path.is_file():
        raise SpiceInspectionError("Kernel artifact path is outside the configured storage root")

    digest = hashlib.sha256()
    with resolved_path.open("rb") as artifact_file:
        while chunk := artifact_file.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise SpiceInspectionError("Stored kernel artifact no longer matches its recorded SHA-256")

    worker_path = Path(__file__).with_name("inspect_worker.py")
    backend_root = Path(__file__).resolve().parents[2]
    try:
        completed = subprocess.run(
            [sys.executable, str(worker_path), str(resolved_path), expected_type],
            cwd=backend_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_INSPECTION_SECONDS,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired as error:
        raise SpiceInspectionError("SPICE inspection exceeded its time limit") from error
    except OSError as error:
        raise SpiceInspectionError("Unable to start the SPICE inspection worker") from error

    if completed.returncode != 0:
        try:
            detail = json.loads(completed.stdout).get("detail", "CSPICE rejected the artifact")
        except (json.JSONDecodeError, AttributeError):
            detail = "CSPICE inspection worker failed"
        raise SpiceInspectionError(str(detail)[:500])

    try:
        result = json.loads(completed.stdout)
        import spiceypy

        return SpiceKernelInspectionRecord(
            kernel_id=kernel_id,
            artifact_sha256=actual_sha256,
            toolkit_version=spiceypy.__version__,
            inspected_at=__import__("datetime").datetime.now(
                __import__("datetime").UTC
            ),
            **result,
        )
    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as error:
        raise SpiceInspectionError("SPICE inspection worker returned an invalid result") from error
