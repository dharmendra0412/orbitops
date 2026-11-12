# ORBITOPS — System Architecture

**Status:** Final review proposal pending human approval  
**Scope:** Hackathon MVP — Lunar Polar Robotic Lander  
**Date:** 2026-11-12

## Purpose and constraints

ORBITOPS is an educational mission-design game. A team of up to four people configures one spacecraft and mission, then runs a deterministic, server-authoritative simulation. Scientific provenance is part of the product: each value is classified as `sourced`, `calculated`, or `illustrative`. This is a game and learning aid, not a flight-design or operational tool.

MVP priorities are a usable mission-design loop, transparent engineering trade-offs, repeatable results, and a credible report. Real-time terrain ray tracing, high-fidelity orbit propagation, live NASA API dependence, autonomous AI design, and production-scale multiplayer are deferred.

## Context and deployment view

```text
Browser (React/TypeScript, Zustand)
  | HTTPS REST: auth, lobby, design, catalog, run, report
  | WSS: authenticated room commands, presence and run status
  v
FastAPI application (Render)
  |-- identity/session and authorization
  |-- mission/design domain service
  |-- deterministic simulation modules
  |-- optional non-authoritative advisor adapter (deferred from MVP)
  |-- cached NASA dataset read service
  |-- PostgreSQL access
  v
Supabase PostgreSQL + Storage (versioned NASA-derived assets)

Vercel serves the static web client.
```

Vercel serves the static web client. Render hosts one FastAPI instance for MVP. Runs are bounded to the instance execution budget; no worker, broker, or Supabase Realtime service is required. Supabase provides PostgreSQL and Auth. FastAPI verifies JWTs and authorizes all writes. No service-role key is shipped to a client.

## Architecture decisions

| Decision | Selection and reason | Alternatives considered |
|---|---|---|
| Backend authority | FastAPI validates designs, executes simulation and computes score. Prevents divergent client answers and supports replay. | Client simulation (trust/drift risk); separate simulation microservice (later only if load requires it). |
| Modular monolith | Domain modules in one deployable backend keep deployment and transactions simple while preserving seams. | Microservices (operational burden); one unstructured route module (poor testability). |
| REST + authoritative WebSocket | REST serves catalog/design/report/recovery; FastAPI validates, commits and sequences collaborative commands before broadcasting. | Supabase Realtime (second authority); polling only (less responsive). |
| PostgreSQL | Relational integrity for users, rooms, designs, catalog versions and immutable runs; JSONB for versioned snapshots. | Document DB; local-only state. |
| Snapshot-pinned runs | A run stores exact design, catalog, ruleset, data and engine versions plus seed. | Recompute against current data (not reproducible after updates). |
| Simplified polar environment | Curated, precomputed illumination bands and scenario timeline for fixed site, with caveats. | Full SPICE + DEM ray tracing in gameplay; static constant sunlight. |
| Frontend rendering | Direct Three.js scene integrated with React; engineering truth remains in ordinary UI/report values. | Hand-built WebGL abstraction; 3D as sole interface. |
| AI boundary | Deferred from MVP; future suggestions only, with backend revalidation. | AI writes score or simulation state (prohibited). |

## Quality attributes

- **Reproducibility:** same immutable inputs, engine version and seed yield the same canonical result under the pinned runtime.
- **Explainability:** each constraint/score contribution includes inputs, equation/rule identifier, units and provenance.
- **Responsiveness:** design validation should feel interactive; bounded runs report terminal status by run ID; interrupted runs fail explicitly and may be retried from a frozen snapshot using a new command ID.
- **Resilience:** cached scientific snapshots allow gameplay without NASA network availability.
- **Accessibility:** essential design, status and report information is available in semantic 2D UI, not only 3D or color.
- **Scope control:** one scenario, a small curated catalog, fixed presets and one simulation fidelity tier.

## Trust boundaries

Browser input is untrusted. Backend validates identifiers, units, bounds, ownership and state transitions. Supabase RLS is defense in depth. WebSocket mission membership is checked before room data is sent and again for every durable command. AI and external data providers are untrusted inputs; AI output is schema-validated and NASA assets are staged, checksummed, reviewed and pinned before use.

## Module map

**Frontend:** mission briefing, workshop, catalog browser, resource dashboard, fixed site/environment briefing, simulation timeline, 3D viewer, collaboration panel, report/replay.  
**Backend:** identity/authorization, mission domain, catalog, design validation, simulation orchestrator, independent engineering modules, event generator, scorer, data manifest service, collaboration gateway, report service.  
**Persistence:** normalized collaboration and identity records plus immutable, versioned input/output snapshots.

## Risks and limits

The largest architectural risk is presenting a simplified energy, illumination or link model as flight-accurate. Make fidelity and units visible. WebSocket command delivery may duplicate or reorder messages; all commands need IDs and sequence checks. Determinism can be compromised by unpinned catalog data, floating-point/platform behavior, or random calls outside a seeded generator. See `TECHNICAL_DECISIONS.md` and the detailed specifications.

## Final architecture decision (2026-11-12)

The primary scenario is a **stationary Lunar Polar Robotic Lander**. The deployable MVP is one FastAPI instance on Render, PostgreSQL and Supabase Auth, Vercel static frontend, FastAPI WebSockets for authoritative collaboration, direct Three.js visualization, deterministic backend simulation, and cached NASA dataset snapshots. Supabase Realtime, microservices, Redis, task brokers and separate worker infrastructure are removed from MVP. Keep runs bounded to one instance; reduce simulation output/time budget before adding infrastructure.

Supabase JWT signature, issuer, audience and expiry are verified by FastAPI; backend checks mission membership and role on every HTTP/WebSocket action. This removes duplicate synchronization paths and keeps one-instance deployment reviewable. Direct Three.js avoids a React renderer abstraction while retaining visual context.

Run computation is bounded to one active simulation at a time in the same FastAPI process/threadpool; this is not a worker process or queue. The WebSocket event loop remains responsive, but MVP need only publish terminal run state. If host/request budgets are exceeded, reduce output density/scope. The original requested filename `SYSTEM_ARCHITECTURE.md` maps to this `ARCHITECTURE.md`; no duplicate architecture file is introduced.

## Strict MVP contract

- One stationary Lunar Polar Robotic Lander. The actual named lunar site and dataset are **NOT YET APPROVED**; a cached site manifest is created only after R1 approval.
- Exactly 30 landed days: `2,592,000 s = 720 × 3,600 s`.
- Illustrative transfer requirement 700 m/s, descent requirement 1,300 m/s, Isp 300 s, mission-level propellant 360 kg.
- Illustrative procurement cap 140 credits; minimum catalog design 118 credits.
- Each run pins catalog, environment, engine, ruleset, execution profile, `lander-score-v2`, seed and immutable revision.
- `RUNNING` transitions only to `COMPLETED` or `FAILED`.
- Simulated mission failure is a completed report with `mission_success=false` and numeric score; engine/infrastructure failure has `score=null`.
- Detailed arithmetic, schema and socket ordering remain in the linked specifications.

Implementation remains pending the human decisions in `TECHNICAL_DECISIONS.md`.

## References

- NASA, [Moon Base Environment](https://www.nasa.gov/reference/moonbase-environment/).
- NASA Science, [Shadows Near the Moon’s South Pole](https://science.nasa.gov/resource/shadows-near-the-moons-south-pole/).
- NASA Science, [LRO Data Products](https://science.nasa.gov/mission/lro/data-products/).

