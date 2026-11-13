"""Resource-limited subprocess for read-only SPICE kernel metadata inspection."""
import json  # noqa: I001
import sys
from pathlib import Path


MAX_OBJECT_IDS = 256
MAX_COVERAGE_INTERVALS_PER_OBJECT = 128
SPICE_CELL_CAPACITY = 20_000


def apply_process_limits() -> None:
    """Apply POSIX resource limits before importing native CSPICE bindings.

    Non-POSIX platforms without the resource module retain the parent process
    timeout and private-snapshot protections. On POSIX, a failed limit
    installation is fatal: inspection must not silently continue unbounded.
    """
    try:
        import resource
    except ImportError:
        return

    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, 2 * 1024 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def inspect_kernel(path: Path, expected_type: str) -> dict:
    # Importing SpiceyPy loads native CSPICE code, so this must remain inside
    # the inspection function and after apply_process_limits() in main().
    import spiceypy as spice

    architecture, detected_type = spice.getfat(str(path))
    if detected_type.upper() != expected_type.upper():
        raise ValueError(
            f"Registered type {expected_type} does not match detected type {detected_type}"
        )

    result = {
        "detected_architecture": architecture,
        "detected_kernel_type": detected_type,
        "object_ids": [],
        "frame_class_ids": [],
        "coverage_intervals": [],
        "metadata_truncated": False,
        "inspection_scope": "format_header_and_supported_binary_index_metadata",
    }

    if expected_type == "SPK":
        ids = spice.spkobj(str(path), spice.cell_int(SPICE_CELL_CAPACITY))
        object_ids = [int(value) for value in ids]
        result["object_ids"] = object_ids[:MAX_OBJECT_IDS]
        result["metadata_truncated"] = len(object_ids) > MAX_OBJECT_IDS

        for object_id in object_ids[:MAX_OBJECT_IDS]:
            coverage = spice.spkcov(
                str(path), object_id, spice.cell_double(SPICE_CELL_CAPACITY)
            )
            interval_count = spice.wncard(coverage)
            intervals = []
            for index in range(min(interval_count, MAX_COVERAGE_INTERVALS_PER_OBJECT)):
                start_et, end_et = spice.wnfetd(coverage, index)
                intervals.append({"start_et_seconds": float(start_et), "end_et_seconds": float(end_et)})
            result["coverage_intervals"].append(
                {
                    "object_id": object_id,
                    "intervals": intervals,
                    "truncated": interval_count > MAX_COVERAGE_INTERVALS_PER_OBJECT,
                }
            )
            if interval_count > MAX_COVERAGE_INTERVALS_PER_OBJECT:
                result["metadata_truncated"] = True

    elif expected_type == "PCK" and architecture.upper() == "DAF":
        ids = spice.cell_int(SPICE_CELL_CAPACITY)
        spice.pckfrm(str(path), ids)
        result["frame_class_ids"] = [int(value) for value in ids[:MAX_OBJECT_IDS]]
        result["metadata_truncated"] = len(ids) > MAX_OBJECT_IDS

    elif expected_type == "DSK":
        ids = spice.dskobj(str(path))
        result["object_ids"] = [int(value) for value in ids[:MAX_OBJECT_IDS]]
        result["metadata_truncated"] = len(ids) > MAX_OBJECT_IDS

    return result


def main() -> int:
    apply_process_limits()
    path = Path(sys.argv[1]).resolve(strict=True)
    expected_type = sys.argv[2]
    try:
        print(json.dumps(inspect_kernel(path, expected_type), separators=(",", ":")))
        return 0
    except Exception as error:  # noqa: BLE001
        # Serialize parser failures instead of returning an uncontrolled traceback.
        print(json.dumps({"error": type(error).__name__, "detail": str(error)[:500]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
