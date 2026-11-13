"""Parent-process integrity checks and bounded invocation for SPICE frame transforms."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from app.ephemeris.kernels import SpiceFrameTransformRecord, SpiceFrameTransformRequest  # noqa: I001


MAX_FRAME_TRANSFORM_SECONDS = 12
MAX_FK_TRANSFORM_BYTES = 10 * 1024 * 1024


class SpiceFrameTransformError(Exception):
    """Raised when a registered FK cannot safely perform a frame transformation."""


def transform_frame(
    *,
    kernel_id: str,
    request: SpiceFrameTransformRequest,
    expected_sha256: str,
    storage_root: Path,
) -> SpiceFrameTransformRecord:
    """Verify a single acquired FK and run a bounded inertial/fixed-frame transform."""
    root = storage_root.resolve()
    artifact_path = root / "sha256" / expected_sha256[:2] / expected_sha256
    if artifact_path.is_symlink():
        raise SpiceFrameTransformError("Content-addressed FK artifact must not be a symbolic link")

    try:
        resolved_path = artifact_path.resolve(strict=True)
    except FileNotFoundError as error:
        raise SpiceFrameTransformError("Registered FK artifact is missing from storage") from error

    if not resolved_path.is_relative_to(root) or not resolved_path.is_file():
        raise SpiceFrameTransformError("FK artifact path is outside the configured storage root")
    if resolved_path.stat().st_size > MAX_FK_TRANSFORM_BYTES:
        raise SpiceFrameTransformError("FK artifact exceeds the 10 MiB transformation limit")

    digest = hashlib.sha256()
    with resolved_path.open("rb") as artifact_file:
        while chunk := artifact_file.read(1024 * 1024):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise SpiceFrameTransformError("Stored FK artifact no longer matches its recorded SHA-256")

    worker_path = Path(__file__).with_name("frame_worker.py")
    backend_root = Path(__file__).resolve().parents[2]
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                str(worker_path),
                str(resolved_path),
                expected_sha256,
                request.from_frame,
                request.to_frame,
                str(request.et_seconds),
                request.transform_type,
                json.dumps(request.vector, separators=(",", ":")),
            ],
            cwd=backend_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_FRAME_TRANSFORM_SECONDS,
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONDONTWRITEBYTECODE": "1",
                **{key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ},
            },
        )
    except subprocess.TimeoutExpired as error:
        raise SpiceFrameTransformError("SPICE frame transformation exceeded its time limit") from error
    except OSError as error:
        raise SpiceFrameTransformError("Unable to start the SPICE frame transformation worker") from error

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SpiceFrameTransformError("SPICE frame worker returned an invalid result") from error

    if completed.returncode != 0:
        raise SpiceFrameTransformError(str(result.get("detail", "CSPICE rejected the frame transformation"))[:500])

    try:
        toolkit_version = version("spiceypy")
        return SpiceFrameTransformRecord(
            kernel_id=kernel_id,
            artifact_sha256=actual_sha256,
            toolkit_version=toolkit_version,
            from_frame=request.from_frame,
            to_frame=request.to_frame,
            et_seconds=request.et_seconds,
            transform_type=request.transform_type,
            matrix=result["matrix"],
            input_vector=request.vector,
            output_vector=result["output_vector"],
            transformed_at=datetime.now(UTC),
        )
    except PackageNotFoundError as error:
        raise SpiceFrameTransformError(
            "SPICE frame transformation is unavailable; install the pinned spice optional dependency"
        ) from error
    except (KeyError, TypeError, ValueError) as error:
        raise SpiceFrameTransformError("SPICE frame worker returned an invalid transformation result") from error
