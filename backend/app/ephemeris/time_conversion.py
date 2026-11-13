"""Controlled SPICE time conversion using an acquired and inspected LSK artifact."""
import json  # noqa: I001
import os
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from app.ephemeris.artifact_snapshot import ArtifactSnapshotError, verified_artifact_snapshot
from app.ephemeris.kernels import SpiceTimeConversionRecord


MAX_CONVERSION_SECONDS = 12
MAX_LSK_CONVERSION_BYTES = 10 * 1024 * 1024


class SpiceTimeConversionError(Exception):
    """Raised when a registered LSK cannot safely perform a time conversion."""


def _run_time_worker(
    *,
    kernel_id: str,
    mode: str,
    value: str,
    expected_sha256: str,
    storage_root: Path,
    input_utc: str | None = None,
    input_et_seconds: float | None = None,
    precision: int = 6,
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

    if not resolved_path.is_relative_to(root):
        raise SpiceTimeConversionError("LSK artifact path is outside the configured storage root")

    worker_path = Path(__file__).with_name("time_worker.py")
    backend_root = Path(__file__).resolve().parents[2]
    try:
        with verified_artifact_snapshot(
            resolved_path,
            expected_sha256=expected_sha256,
            max_bytes=MAX_LSK_CONVERSION_BYTES,
            artifact_label="LSK",
        ) as (snapshot_path, actual_sha256):
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(worker_path),
                    str(snapshot_path),
                    mode,
                    value,
                    str(precision),
                    expected_sha256,
                ],
                cwd=backend_root,
                capture_output=True,
                text=True,
                check=False,
                timeout=MAX_CONVERSION_SECONDS,
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
    except ArtifactSnapshotError as error:
        if "exceeds the" in str(error):
            raise SpiceTimeConversionError(
                f"LSK artifact exceeds the {MAX_LSK_CONVERSION_BYTES} byte conversion limit"
            ) from error
        raise SpiceTimeConversionError(str(error)) from error
    except subprocess.TimeoutExpired as error:
        raise SpiceTimeConversionError("SPICE time conversion exceeded its time limit") from error
    except OSError as error:
        raise SpiceTimeConversionError("Unable to start the SPICE time conversion worker") from error

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SpiceTimeConversionError("SPICE time worker returned an invalid result") from error

    if completed.returncode != 0:
        raise SpiceTimeConversionError(str(result.get("detail", "CSPICE rejected the time input"))[:500])

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
            input_utc=input_utc,
            input_et_seconds=input_et_seconds,
            conversion_direction=mode,
            conversion_scope=f"{mode}_using_single_registered_lsk",
            et_seconds=float(result["et_seconds"]),
            normalized_utc=str(result["normalized_utc"]),
            converted_at=datetime.now(UTC),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise SpiceTimeConversionError("SPICE time worker returned an invalid conversion record") from error


def convert_utc_to_et(
    *,
    kernel_id: str,
    utc_time: str,
    expected_sha256: str,
    storage_root: Path,
) -> SpiceTimeConversionRecord:
    """Convert an explicitly UTC-tagged string to ET seconds past J2000 TDB."""
    return _run_time_worker(
        kernel_id=kernel_id,
        mode="utc_to_et",
        value=utc_time,
        expected_sha256=expected_sha256,
        storage_root=storage_root,
        input_utc=utc_time,
    )


def convert_et_to_utc(
    *,
    kernel_id: str,
    et_seconds: float,
    precision: int,
    expected_sha256: str,
    storage_root: Path,
) -> SpiceTimeConversionRecord:
    """Convert finite ET seconds past J2000 TDB to UTC using the selected LSK."""
    return _run_time_worker(
        kernel_id=kernel_id,
        mode="et_to_utc",
        value=str(et_seconds),
        expected_sha256=expected_sha256,
        storage_root=storage_root,
        input_et_seconds=et_seconds,
        precision=precision,
    )
