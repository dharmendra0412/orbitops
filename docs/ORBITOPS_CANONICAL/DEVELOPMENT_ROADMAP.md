# ORBITOPS — Development Roadmap

The roadmap sequences dependencies for a hackathon MVP. Estimates and timeline must be fitted to the actual event calendar/team capacity; none are assumed here.

## Phase 0 — Scope and evidence

- Decide target platform, user age/accessibility expectations, monetary units, site preset, scoring weights and team workflow.
- Curate a small source manifest; mark all game-balancing values; review source usage/attribution.
- Freeze MVP fidelity statement and acceptance scenarios.

**Exit:** approved scenario brief, value taxonomy and initial illustrative catalog.

## Phase 1 — Contracts and vertical foundation

- Define typed design, catalog, provenance, validation and run-result schemas.
- Set up React/TypeScript/Vite/Tailwind and FastAPI/Pydantic/Postgres migrations.
- Implement auth/membership model and OpenAPI error conventions.

**Exit:** browser can load scenario/catalog and create/read a mission.

## Phase 2 — Deterministic engineering core

- Implement pure mass, power, energy, data, propulsion, communication and constraint modules.
- Implement fixed-step/event-step simulator, seed handling, run snapshots and scoring breakdown.
- Add unit/invariant/repeatability tests as code is implemented.

**Exit:** CLI or API can run a canonical mission twice and return repeatable metrics/events.

## Phase 3 — Design workshop

- Catalog selection, slots and component quantities; display fixed mission duration and, only after R1 approval, the selected site schedule without player-editable controls.
- Backend validation and resource dashboard, with pending/accepted revision behavior.
- Save, clone and compare designs.

**Exit:** user can create a feasible and infeasible design and understand why.

## Phase 4 — Simulation and report

- Run lifecycle, event timeline and report/replay views.
- Explain constraints, score weights, provenance and scenario limitations.

**Exit:** complete end-to-end single-player loop; resilient retry and report retrieval.

## Phase 5 — Collaboration and 3D

- Four-player room membership, command IDs/revisions, reconnect snapshot, presence and conflict UX.
- Add accessible 3D lunar scene as a visual complement with site and illumination annotations.

**Exit:** two clients edit without silent lost updates; scene never determines engineering truth.

## Phase 6 — Advisor, polish and deployment

- Optional AI advisor proposes bounded suggestions/explanations; validate every suggestion through backend. Advisor is deferred if it threatens the core loop.
- Deploy Vercel/Render/Supabase, configure secrets, CORS, migrations, backups/retention, monitoring and demo seed data.
- Run security review, manual gameplay walkthrough and judge-facing demo rehearsal.

**Exit:** reproducible public demo and documented known limitations.

## Critical path and deferrals

Critical path: science scope/provenance → catalog and scenario contract → deterministic engine → backend API → design UI → run/report → multiplayer and 3D polish. Defer multiple missions, free-form orbital mechanics, live ephemeris calls, live terrain processing, detailed thermal/subsystem models, user-created hardware, persistent chat, matchmaking, advanced AI agents and microservices until the vertical slice works.

## Final sequence and acceptance gates

1. Human approves stationary lander scope, named site/schedule fidelity, catalog values and score rubric.
2. Define shared Pydantic/OpenAPI plus WebSocket discriminated schemas; create Postgres migrations, JWT verification and role matrix.
3. Seed immutable `lander-mvp-1`, environment and ruleset versions with provenance classes.
4. Implement pure engineering modules and 30-day/720-step deterministic phase simulator; verify resource invariants and event reproducibility.
5. Build solo design workshop, backend validation, run and transparent report; frontend never authors final engineering results.
6. Add authoritative FastAPI WebSocket commands, idempotency, optimistic revisions, ordered durable events and reconnect snapshots.
7. Add direct Three.js visual context with accessible non-3D equivalents and science caveats.
8. Deploy one Render instance with Supabase Postgres/Auth and Vercel; measure run budget and test restart/error behavior. If runtime is too long, reduce output density/scope; do not add infrastructure during MVP.

## MVP gates

- Launcher/transfer/descent checks.
- Fixed 30-day/720-step duration.
- Science, segment energy, data, contact, budget and event loop.
- Version-pinned repeatable result.
- Visible score explanations.
- Four-person room and two-client concurrent edit race produces accepted revision plus conflict (no overwrite).
- Reconnect restores latest state.
- NASA outage does not block runs.
- One-instance deployment succeeds.

The segment-second battery vectors (including charge/discharge losses, clipping and brownout), propulsion ledger, `lander-score-v2` examples, catalog property/quantity normalization, and command/reconnect protocol in the final consistency audit are implementation acceptance fixtures. They supersede explicitly marked shorthand values in older sections. MVP remains one stationary lander, one named site preset, 30 landed days, exactly 720 3,600-second outer steps, 700 m/s transfer requirement, 1,300 m/s descent requirement, illustrative 300 s Isp and 360 kg propellant, and 140-credit budget with 118-credit minimum configuration.

