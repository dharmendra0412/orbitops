# ORBITOPS

**Engineering-grade lunar mission design and operations platform.**

ORBITOPS is being developed as a scientific-data-driven engineering application. Engineering outputs must be traceable to versioned inputs, documented equations, explicit assumptions, and verification/validation evidence. The application must never present an unvalidated model as flight-qualified or operationally safe.

## Repository status

The `engineering-grade-foundation` branch establishes the initial application foundation. It is not a completed mission-analysis product. No lunar site, mission profile, component specification, or model has been silently approved by this scaffold.

## Current stack

- Backend: Python 3.11+, FastAPI, Pydantic, SQLite
- Frontend: React, TypeScript, Vite
- Tests: pytest, FastAPI TestClient
- CI: GitHub Actions

## Implemented foundation

- Engineering-value contracts with unit dimension and provenance metadata.
- Versioned ideal rocket-equation model with source-traceable standard gravity and explicit unvalidated limitations.
- Constant-power energy balance model for a fixed interval, with traceable inputs and explicit battery/mission exclusions.
- Append-only SQLite model-run registry that preserves inputs, outputs, equation/model versions, assumptions and limitations.
- Dataset manifest validation and immutable metadata registry.
- Bounded SHA-256 upload inspection (100 MiB maximum); uploaded bytes are not persisted.
- Interactive frontend file-inspection panel and API connectivity indicator.
- Automated backend lint/tests and frontend typecheck/build.

The checksum endpoint computes a digest for uploaded bytes; it does not authenticate a source, download remote data, or establish scientific suitability. The manifest registry stores metadata only, not dataset files.

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

## Dataset API

- `POST /api/v1/datasets/checksum` — multipart upload; returns filename, media type, byte size, and SHA-256. Maximum 100 MiB; no persistence.
- `POST /api/v1/datasets/manifests/validate` — validates dataset metadata without saving.
- `POST /api/v1/datasets/manifests` — registers an immutable manifest; duplicate IDs return HTTP 409.
- `GET /api/v1/datasets/manifests` — paginated manifest listing.
- `GET /api/v1/datasets/manifests/{manifest_id}` — retrieve a registered manifest.
- `POST /api/v1/models/propulsion/ideal-delta-v` — calculate ideal delta-v from traceable mass and specific-impulse inputs; output remains unvalidated.
- `POST /api/v1/models/power/simple-energy-balance` — compare average supply/load power over a fixed interval; output remains unvalidated.
- `GET /api/v1/models/runs` and `GET /api/v1/models/runs/{run_id}` — list and retrieve persisted model-run snapshots.

See [the data ingestion contract](docs/DATA_INGESTION_CONTRACT.md), [the manifest registry contract](docs/MANIFEST_REGISTRY.md), [the candidate lunar data-source review](docs/DATA_SOURCE_REVIEW.md), and [the ideal rocket-equation model note](docs/PROPULSION_IDEAL_ROCKET_EQUATION.md), and [the power energy-balance model note](docs/POWER_SIMPLE_ENERGY_BALANCE.md), and [the model-run registry contract](docs/MODEL_RUN_REGISTRY.md).

## Engineering integrity rules

1. Every physical quantity carries a unit.
2. Every sourced value has a source/product/version reference.
3. Every derived value records its equation/model version and input references.
4. Unvalidated models are explicitly marked `UNVALIDATED`.
5. Missing data is represented as missing—not replaced with invented values.
6. Model verification, validation, uncertainty, and intended-use limits are release requirements.
7. No flight certification or operational-safety claim is made without the relevant formal evidence and authorization.

## Planned engineering modules

After controlled data ingestion, the next phases are scientific source curation and independently testable models for geometry, trajectory/propulsion, power, thermal behavior, communications, and mission operations. Each model must have a defined intended use and acceptance evidence before it can produce an engineering-grade result.

## Branch policy

Work on feature branches. Review changes through pull requests. Do not push unreviewed engineering changes directly to `main`.
