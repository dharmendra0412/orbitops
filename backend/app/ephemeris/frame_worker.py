"""Bounded SPICE position/state frame transform using one fixed-frame FK."""
import hashlib  # noqa: I001
import json
import math
import sys
from pathlib import Path

import spiceypy as spice


MAX_FK_BYTES = 10 * 1024 * 1024


def apply_process_limits() -> None:
    """Apply best-effort POSIX limits before invoking native CSPICE routines."""
    try:
        import resource
    except ImportError:
        return

    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, 2 * 1024 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _frame_class(name: str) -> int:
    frame_id = int(spice.namfrm(name))
    if frame_id == 0:
        raise ValueError(f"Unknown SPICE frame: {name}")
    frame_info = spice.frinfo(frame_id)
    if len(frame_info) == 4:
        _center, frame_class, _class_id, found = frame_info
        if not found:
            raise ValueError(f"No SPICE frame definition found for: {name}")
    else:
        _center, frame_class, _class_id = frame_info
    if int(frame_class) not in (1, 4):
        raise ValueError(
            f"Frame {name} uses unsupported SPICE frame class {frame_class}; "
            "only inertial class 1 and fixed-offset TK class 4 are supported"
        )
    return int(frame_class)


def main() -> int:
    apply_process_limits()
    path = Path(sys.argv[1]).resolve(strict=True)
    expected_sha256 = sys.argv[2]
    from_frame = sys.argv[3]
    to_frame = sys.argv[4]
    et_seconds = float(sys.argv[5])
    transform_type = sys.argv[6]
    vector = json.loads(sys.argv[7]) if sys.argv[7] != "null" else None

    try:
        if path.stat().st_size > MAX_FK_BYTES:
            raise ValueError("FK artifact exceeds the 10 MiB transformation limit")
        digest = hashlib.sha256()
        with path.open("rb") as artifact_file:
            while chunk := artifact_file.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != expected_sha256:
            raise ValueError("FK artifact changed after the parent integrity check")
        if not math.isfinite(et_seconds):
            raise ValueError("ET seconds must be finite")

        architecture, kernel_type = spice.getfat(str(path))
        if architecture.upper() != "KPL" or kernel_type.upper() != "FK":
            raise ValueError("Frame transformation requires a text FK (KPL/FK) artifact")

        spice.furnsh(str(path))
        _frame_class(from_frame)
        _frame_class(to_frame)

        if transform_type == "position":
            matrix = spice.pxform(from_frame, to_frame, et_seconds)
        elif transform_type == "state":
            matrix = spice.sxform(from_frame, to_frame, et_seconds)
        else:
            raise ValueError("Unsupported frame transformation type")

        matrix_values = [[float(value) for value in row] for row in matrix]
        output_vector = None
        if vector is not None:
            output_vector = [
                sum(matrix_values[row][column] * float(vector[column]) for column in range(len(vector)))
                for row in range(len(vector))
            ]

        print(json.dumps({
            "matrix": matrix_values,
            "output_vector": output_vector,
            "from_frame": from_frame,
            "to_frame": to_frame,
            "et_seconds": et_seconds,
            "transform_type": transform_type,
            "detected_architecture": architecture,
            "detected_kernel_type": kernel_type,
        }, separators=(",", ":")))
        return 0
    except Exception as error:  # noqa: BLE001
        print(json.dumps({"error": type(error).__name__, "detail": str(error)[:500]}))
        return 2
    finally:
        spice.kclear()


if __name__ == "__main__":
    raise SystemExit(main())
