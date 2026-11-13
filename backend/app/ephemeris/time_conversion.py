"""Controlled UTC-to-ET conversion using an acquired and inspected LSK artifact."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from app.ephemeris.kernels import SpiceTimeConversionRecord


MAX_CONVERSION_SECONDS = 12
HASH_CHUNK_BYTES = 1024 * 1024


class SpiceTimeConversionError(Exception):
    """Raised when a registered LSK cannot safely perform a time conversion."""


def convert_utc_to_et(
    *,
    kernel_id: str,
    utc_time: str,
    expected_sha256: str,
    storage_root: Path,
) -> SpiceTimeConversionRecord:
    """Verify the acquired LSK bytes, then convert in a bounded child process."""
    root = storage_root.resolve()
    artifact_path = root / "sha256" / expected_sha256[:2] / expected_sha256
    if artifact_path.is_symlink():
        raise SpiceTimeConversionError("Content-addressed LSK artifact must not be a symbolic link")

    try:
        resolved_path = artifact_path.resolve(strict=True)
    except FileNotFoundError as error:
        raise SpiceTimeConversionError("Registered LSK artifact is missing from storage") from error

    if not resolved_path.is_relative_to(root) or not resolved_path.is_file():
        raise SpiceTimeConversionError("LSK artifact path is outside the configured storage root")

    digest = hashlib.sha256()
    with resolved_path.open("rb") as artifact_file:
        while chunk := artifact_file.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise SpiceTimeConversionError("Stored LSK artifact no longer matches its recorded SHA-256")

    worker_path = Path(__file__).with_name("time_worker.py")
    backend_root = Path(__file__).resolve().parents[2]
    try:
        completed = subprocess.run(
            [sys.executable, "-I", str(worker_path), str(resolved_path), utc_time],
            cwd=backend_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_CONVERSION_SECONDS,
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONDONTWRITEBYTECODE": "1",
                **{key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ},
            },
        )
    except subprocess.TimeoutExpired as error:
        raise SpiceTimeConversionError("SPICE time conversion exceeded its time limit") from error
    except OSError as error:
        raise SpiceTimeConversionError("Unable to start the SPICE time conversion worker") from error

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SpiceTimeConversionError("SPICE time worker returned an invalid result") from error

    if completed.returncode != 0:
        raise SpiceTimeConversionError(str(result.get("detail", "CSPICE rejected the UTC input"))[:500])

    try:
        toolkit_version = version("spiceypy")
    except PackageNotFoundError as error:
        raise SpiceTimeConversionError(
            "SPICE time conversion is unavailable; install the pinned spice optional dependency"
        ) from error

    try:
        return SpiceTimeConversionRecord(
            kernel_id=kernel_id,
            artifact_sha256=actual_sha256,
            toolkit_version=toolkit_version,
            input_utc=utc_time,
            et_seconds=float(result["et_seconds"]),
            normalized_utc=str(result["normalized_utc"]),
            converted_at=datetime.now(UTC),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise SpiceTimeConversionError("SPICE time worker returned an invalid conversion record") from error
