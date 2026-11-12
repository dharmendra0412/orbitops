# ORBITOPS

**Engineering-grade lunar mission design and operations platform.**

ORBITOPS is being developed as a scientific-data-driven engineering application. Engineering outputs must be traceable to versioned inputs, documented equations, explicit assumptions, and verification/validation evidence. The application must never present an unvalidated model as flight-qualified or operationally safe.

## Repository status

The `engineering-grade-foundation` branch establishes the initial application foundation. It is not a completed mission-analysis product. No lunar site, mission profile, component specification, or model has been silently approved by this scaffold.

## Current stack

- Backend: Python 3.11+, FastAPI, Pydantic
- Frontend: React, TypeScript, Vite
- Tests: pytest, FastAPI TestClient
- CI: GitHub Actions

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

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL=http://127.0.0.1:8000` in `frontend/.env.local` when the API is not served from the same origin.

## Engineering integrity rules

1. Every physical quantity carries a unit.
2. Every sourced value has a source/product/version reference.
3. Every derived value records its equation/model version and input references.
4. Unvalidated models are explicitly marked `UNVALIDATED`.
5. Missing data is represented as missing—not replaced with invented values.
6. Model verification, validation, uncertainty, and intended-use limits are release requirements.
7. No flight certification or operational-safety claim is made without the relevant formal evidence and authorization.

## Planned engineering modules

The first implementation phases will establish controlled data ingestion and provenance, then independently testable engineering models for geometry, trajectory/propulsion, power, thermal behavior, communications, and mission operations. Each model must have a defined intended use and acceptance evidence before it can produce an engineering-grade result.

## Branch policy

Work on feature branches. Review changes through pull requests. Do not push unreviewed engineering changes directly to `main`.
