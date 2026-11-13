"""Print a read-only audit of local SPICE artifact storage."""

from __future__ import annotations

import argparse
import json

from app.settings import settings
from app.storage.spice_artifact_recovery import audit_spice_artifact_storage
from app.storage.spice_kernels import SpiceKernelStore


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit SPICE artifact storage without modifying or deleting files."
    )
    parser.add_argument(
        "--stale-after-seconds",
        type=int,
        default=3600,
        help="Age threshold for staging-file review candidates (default: 3600).",
    )
    args = parser.parse_args()
    store = SpiceKernelStore(settings.database_path)
    report = audit_spice_artifact_storage(
        settings.spice_kernel_storage_path,
        store,
        stale_after_seconds=args.stale_after_seconds,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
