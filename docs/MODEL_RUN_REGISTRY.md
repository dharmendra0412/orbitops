# Model Run Registry

Every successful propulsion or power model API call creates an append-only SQLite
snapshot. The record includes a UUID run identifier, model identifier, model version,
equation identifier, UTC creation timestamp, and the complete calculation result.
The result payload includes the input EngineeringValue records, calculated outputs,
source constants where applicable, assumptions, and limitations.

## Endpoints

- GET /api/v1/models/runs — list runs newest first; supports limit (1–100) and offset.
- GET /api/v1/models/runs/{run_id} — retrieve one complete snapshot.

Model runs are created automatically by:
- POST /api/v1/models/propulsion/ideal-delta-v
- POST /api/v1/models/power/simple-energy-balance

Each calculation response also returns run_id and created_at. Use run_id to retrieve
the stored snapshot later.

## Persistence and integrity boundaries

Model runs and dataset manifests share the configured SQLite database. The schema
version is now 2. SQLite WAL mode is enabled. Run records are append-only through
the current API; no update or delete endpoint is exposed.

This registry is not a tamper-evident audit log: records are not digitally signed,
the database is not replicated, and access control/authentication is not yet
implemented. Deployment operators must protect and back up the database file.
The registry preserves calculation provenance but does not independently validate
the correctness of model equations or input data.
