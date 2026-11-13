# ORBITOPS

**Multi-planetary mission engineering and operations platform.**

ORBITOPS is being developed as a scientific-data-driven engineering application. Engineering outputs must be traceable to versioned inputs, documented equations, explicit assumptions, and verification/validation evidence. The application must never present an unvalidated model as flight-qualified or operationally safe.

## Product scope

ORBITOPS targets mission-analysis workflows across all eight planets, with multiple mission archetypes. See [the multi-planetary mission scope](docs/PLANETARY_MISSION_SCOPE.md). Natural satellites, dwarf planets and small bodies are planned catalogue extensions.

## Repository status

See [the current engineering status and remaining release gates](docs/ENGINEERING_STATUS.md). The older `docs/ORBITOPS_CANONICAL/` package is retained as historical project material and is not the source of truth for the engineering-grade branch.

The engineering-grade foundation, mission workspaces, spacecraft configuration, and requirement traceability workstreams are developed on feature branches and remain subject to automated CI and engineering acceptance.

## Current stack

- Backend: Python 3.11+, FastAPI, Pydantic, SQLite
- Frontend: React, TypeScript, Vite
- Tests: pytest, FastAPI TestClient
- CI: GitHub Actions

## Implemented foundation

- Eight-planet destination taxonomy and seven mission archetypes via `GET /api/v1/missions/catalog`; feasibility remains unassessed.
- Persistent mission project workspaces with typed objectives and requirements, immutable numbered revisions, and paginated project listing/retrieval.
- Append-only requirement verification evidence records linked to the latest project revision, with method consistency checks and evidence references.
- Spacecraft component contracts with typed subsystem classification and provenance-aware mass and power values.
- Append-only spacecraft configuration revisions linked to mission projects.
- Requirement-to-component allocation records and a latest-revision traceability matrix, including unallocated requirements, stale component references, and verification evidence counts.
- Model verification/validation evidence registry with derived credibility states for registered model versions.
- Historical mission/spacecraft revision comparison with changed requirement/component detection and impacted-allocation reporting.
- Frontend dataset workflow connecting file checksum inspection to source manifest registration and registered-manifest browsing.
- Consolidated project-scoped engineering review package with findings, completeness state, and JSON export.
- Append-only associations linking registered dataset manifests and model assessment records to mission projects.
- Component mass, user-entered mass margin, and average power generation/load bookkeeping with explicit duty cycles.
- Engineering-value contracts with unit dimension and provenance metadata.
- Versioned ideal rocket-equation, constant-average-power energy-balance, and two-body Keplerian orbital mechanics models; all remain unvalidated.
- Append-only SQLite model-run registry preserving inputs, outputs, equation/model versions, assumptions and limitations.
- Dataset manifest validation, immutable metadata registry and bounded SHA-256 upload inspection (100 MiB maximum); uploaded bytes are not persisted.\n- Bounded PDS4 XML label metadata inspection (5 MiB maximum), rejecting DTD/entity declarations and limiting XML nesting/element count; referenced science-data files are not inspected.

Spacecraft budget calculations are transparent arithmetic summaries, not an integrated spacecraft simulation. They do not model batteries, eclipses, transients, conversion losses, degradation, thermal coupling or component interactions. Schema validation does not authenticate user-supplied source material or certify component suitability.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Health endpoint: `http://127.0.0.1:8000/api/v1/health`

API documentation: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api` requests to `http://127.0.0.1:8000`. Set `VITE_API_BASE_URL` in `frontend/.env.local` only when the API is hosted on a different origin. Configure the backend CORS allowlist for that deployed frontend origin.

## Mission project API

- `POST /api/v1/missions/projects` — create a mission workspace and immutable revision 1.
- `GET /api/v1/missions/projects` — list mission workspaces with limit/offset pagination.
- `GET /api/v1/missions/projects/{project_id}` — retrieve the latest project revision.
- `POST /api/v1/missions/projects/{project_id}/revisions` — append a new immutable revision.
- `POST /api/v1/missions/projects/{project_id}/verification-records` — append verification evidence.
- `GET /api/v1/missions/projects/{project_id}/verification-records` — list recorded evidence.
- `POST /api/v1/missions/projects/{project_id}/traceability/allocations` — append a requirement-to-component allocation.
- `GET /api/v1/missions/projects/{project_id}/traceability/matrix` — retrieve the latest-revision traceability matrix.
- `GET /api/v1/missions/projects/{project_id}/traceability/change-impact` — compare selected mission and spacecraft revisions and identify allocations requiring review. Supply baseline/target revision numbers as query parameters.
- `GET /api/v1/missions/projects/{project_id}/review-package` — compile the current project, spacecraft configuration, budgets, traceability matrix, verification evidence, linked datasets, and linked model assessments into a review package.
- `POST /api/v1/missions/projects/{project_id}/evidence/datasets` and `GET .../evidence/datasets` — link/list registered dataset manifests for a mission.
- `POST /api/v1/missions/projects/{project_id}/evidence/model-assessments` and `GET .../evidence/model-assessments` — link/list model assessment evidence for a mission.

## Spacecraft configuration API

- `POST /api/v1/missions/projects/{project_id}/spacecraft/configuration` — create the first configuration.
- `GET /api/v1/missions/projects/{project_id}/spacecraft/configuration` — retrieve the latest configuration.
- `POST /api/v1/missions/projects/{project_id}/spacecraft/configuration/revisions` — append a configuration revision.
- `GET /api/v1/missions/projects/{project_id}/spacecraft/budgets` — calculate mass and average-power budgets.

Each component contains a subsystem, unique revision-scoped identifier, mass value and optional power draw/generation values. Engineering quantities use the shared EngineeringValue contract, including provenance and credibility metadata. The mass margin is user-specified and is applied to the sum of component masses. Average power is calculated from component power values and explicit duty cycles. These calculations are not a validated spacecraft design or feasibility assessment.

Requirement allocations are append-only and must reference a requirement in the latest mission revision and a component in the latest spacecraft configuration. Allocations do not prove compliance. The matrix flags component references that become stale after a spacecraft configuration revision. The change-impact report compares historical mission and spacecraft snapshots, lists added/removed/modified requirements and components, and flags current allocations linked to modified or removed items. Allocations are not themselves revisioned, and historical verification evidence is not automatically invalidated. Mission requirement evidence is append-only; a recorded `pass` is not independent acceptance, formal closure, safety approval or flight qualification. Evidence references are user-supplied and not authenticated. Authentication and per-user/team authorization are not implemented, so these APIs must not be exposed as a multi-tenant production service.

## Dataset and model APIs

- `POST /api/v1/datasets/checksum` — multipart upload; returns filename, media type, byte size, and SHA-256. Maximum 100 MiB; no persistence.
- `POST /api/v1/datasets/manifests/validate` — validates dataset metadata without saving.
- `POST /api/v1/datasets/manifests` — registers an immutable manifest.
- `GET /api/v1/datasets/manifests` — paginated manifest listing.
- `GET /api/v1/datasets/manifests/{manifest_id}` — retrieve a registered manifest.
- `POST /api/v1/models/propulsion/ideal-delta-v` — calculate ideal delta-v from traceable inputs; output remains unvalidated.
- `POST /api/v1/models/power/simple-energy-balance` — compare average supply/load power over a fixed interval; output remains unvalidated.
- `POST /api/v1/models/orbital-mechanics/circular-orbit` — calculate two-body circular orbital speed.
- `POST /api/v1/models/orbital-mechanics/vis-viva` — calculate elliptical-orbit speed from radius and semi-major axis.
- `POST /api/v1/models/orbital-mechanics/orbital-period` — calculate Keplerian orbital period.
- `POST /api/v1/models/orbital-mechanics/escape-velocity` — calculate local two-body escape velocity.
- `POST /api/v1/models/orbital-mechanics/hohmann-transfer` — estimate ideal two-burn transfer delta-v and transfer time between circular coplanar orbits.
- `GET /api/v1/models/runs` and `GET /api/v1/models/runs/{run_id}` — list and retrieve persisted model-run snapshots.
- `GET /api/v1/models/governance/catalog` — list registered model versions and derived credibility states.
- `POST /api/v1/models/governance/assessments` — append verification or validation evidence for a registered model version.
- `GET /api/v1/models/governance/assessments` — list model assessment records, optionally filtered by model ID/version.

### PDS4 label inspection API\n\n- `POST /api/v1/datasets/pds4/inspect` — inspect a small PDS4 XML label and extract selected identification, observation, file, and array metadata.\n\nThis endpoint is a metadata preview only. It does not perform authoritative PDS4 schema validation, scientific data validation, source authentication, or coordinate/time-system interpretation.\n\n## Engineering integrity rules

1. Every physical quantity carries a unit.
2. Every sourced value has a source/product/version reference.
3. Every derived value records its equation/model version and input references.
4. Unvalidated models are explicitly marked `UNVALIDATED`.
5. Missing data is represented as missing—not replaced with invented values.
6. Model verification, validation, uncertainty, and intended-use limits are release requirements.
7. No flight certification or operational-safety claim is made without the relevant formal evidence and authorization.

## Branch policy

Work on feature branches. Review changes through pull requests. Do not push unreviewed engineering changes directly to `main`.
