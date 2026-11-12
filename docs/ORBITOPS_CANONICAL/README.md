> **Historical documentation notice (2026-11-12):** This folder contains the earlier
> educational mission-simulation concept and its original specifications. The
> engineering-grade foundation branch has since pivoted to traceable scientific
> data, versioned models, and verification evidence. Treat these files as historical
> context only; use the root README and current engineering documents in `docs/`
> for the implemented branch state. No legacy illustrative values are approved
> as engineering specifications.
>
# ORBITOPS Documentation Pack

**Date:** 2026-11-12  
**Status:** Canonical documentation set under R0-approved reconciliation; human approval gates R1–R6 remain open. This is not approval to begin implementation.

## Document index

| File | Purpose |
|---|---|
| `ARCHITECTURE.md` | System context, deployment, trust boundaries and architecture decisions. |
| `SYSTEM_DESIGN.md` | User journey, frontend/backend boundaries, ownership and runtime behavior. |
| `DATABASE_SCHEMA.md` | PostgreSQL tables, constraints, retention, immutability and migrations. |
| `API_SPECIFICATION.md` | REST, WebSocket, auth, idempotency, revision and run-state contracts. |
| `SIMULATION_ENGINE_SPEC.md` | Deterministic simulation, engineering equations, battery dispatch, propulsion and scoring. |
| `COMPONENT_CATALOG_SPEC.md` | Versioned 18-item illustrative spacecraft catalog and property semantics. |
| `TESTING_STRATEGY.md` | Unit, invariant, determinism, integration, security and acceptance fixtures. |
| `DEVELOPMENT_ROADMAP.md` | Phased implementation sequence and MVP gates. |
| `NASA_DATA_SOURCES.md` | Candidate NASA/JPL sources, curation and provenance pipeline. |
| `TECHNICAL_DECISIONS.md` | Decision record, known risks and human approval gates. |

## Canonical MVP baseline

- Stationary Lunar Polar Robotic Lander; actual named site and dataset **NOT YET APPROVED** (R1). No location is selected by this documentation pack.
- 30 landed days, 720 outer steps, 3,600 seconds per step.
- Illustrative: 700 m/s transfer, 1,300 m/s descent, 300 s Isp, 360 kg propellant.
- 140-credit procurement cap; 118-credit minimum catalog build.
- One Render FastAPI instance, Supabase PostgreSQL/Auth, Vercel static frontend, FastAPI WebSockets, direct Three.js.
- Server-authoritative deterministic simulation; cached data; no live NASA dependency during gameplay.

## Corrections applied in this pack

1. `simulation_runs.seed` is `BIGINT` with a uint32 range CHECK; PostgreSQL `INT` cannot represent the full accepted range.
2. Scoring term `F` is pre-touchdown hard-gate feasibility. A landed failure retains `F=1` if those gates passed; the overall landed-failure score is capped at 49.9.

## Important status note

This pack consolidates the supplied specifications and applies the two documented consistency corrections. It does **not** mean the human approval gates have been approved, nor that code has been implemented or tested. Site selection, source-data transformation, game-parameter approval, score approval, collaboration policy and runtime limits remain explicit decisions.

