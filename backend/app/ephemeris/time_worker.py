"""Isolated UTC/ET conversion using exactly one acquired LSK kernel."""

import hashlib
import json
import math
import sys
from pathlib import Path



def apply_process_limits() -> None:
    """Apply POSIX resource limits before importing native CSPICE bindings."""
    try:
        import resource
    except ImportError:
        return

    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, 2 * 1024 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4096, 4096))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main() -> int:
    apply_process_limits()
    import spiceypy as spice

    path = Path(sys.argv[1]).resolve(strict=True)
    mode = sys.argv[2]
    value = sys.argv[3]
    precision = int(sys.argv[4])
    expected_sha256 = sys.argv[5]
    try:
        if path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("LSK artifact exceeds the 10 MiB conversion limit")
        digest = hashlib.sha256()
        with path.open("rb") as artifact_file:
            while chunk := artifact_file.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != expected_sha256:
            raise ValueError("LSK artifact changed after the parent integrity check")

        architecture, kernel_type = spice.getfat(str(path))
        if architecture.upper() != "KPL" or kernel_type.upper() != "LSK":
            raise ValueError("Time conversion requires a text LSK (KPL/LSK) artifact")

        spice.furnsh(str(path))
        if mode == "utc_to_et":
            et_seconds = float(spice.str2et(value))
        elif mode == "et_to_utc":
            et_seconds = float(value)
            if not math.isfinite(et_seconds):
                raise ValueError("ET seconds must be a finite number")
        else:
            raise ValueError("Unsupported SPICE time-conversion direction")

        if not math.isfinite(et_seconds):
            raise ValueError("CSPICE returned a non-finite ET value")
        normalized_utc = spice.et2utc(et_seconds, "ISOC", precision)
        print(json.dumps({
            "et_seconds": et_seconds,
            "normalized_utc": normalized_utc,
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
