# Dataset Manifest Registry

Dataset manifests are stored as immutable JSON snapshots in SQLite. The configured
database path defaults to `data/orbitops.sqlite3` relative to the backend working
directory and can be overridden with the `DATABASE_PATH` environment variable.

## Manifest metadata

Each manifest includes citation text and source/product/version identity. Assets are
classified as source, transformed, or derived. Transformed and derived assets require
a transformation description and transform version. Optional traceability fields
include original units, variable units, coordinate frame, time system, temporal
coverage, spatial resolution, quality/uncertainty notes, and limitations.

## Endpoints

- POST /api/v1/datasets/manifests — register a manifest; returns 201.
- GET /api/v1/datasets/manifests — list manifests; supports limit (1–100) and offset.
- GET /api/v1/datasets/manifests/{manifest_id} — retrieve one manifest.
- POST /api/v1/datasets/manifests/validate — validate only; does not persist.
- POST /api/v1/datasets/checksum — calculate checksum for an upload; does not persist bytes.

Manifest identifiers are primary keys. A duplicate identifier returns HTTP 409;
the application does not overwrite an existing manifest. A new product release or
transformation should receive a new manifest identifier. SQLite uses WAL mode and
a schema version marker. Database files are local application state and must be
backed up and protected by the deployment operator.

The registry stores metadata only. It does not store original or transformed
dataset bytes, independently verify source URLs or licenses, or prove scientific
validity.
