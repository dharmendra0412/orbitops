# ORBITOPS — System Design

## MVP user journey

1. Player selects Lunar Polar Robotic Lander and reads objectives, constraints, fidelity notes and cited science context.
2. Host creates a room and invites up to three collaborators (four members total, including host). A solo path uses the same domain objects.
3. Team receives the fixed 30-day mission profile and the proposed site briefing; it configures a spacecraft from the catalog. The actual named lunar site and dataset are **NOT YET APPROVED** under R1. Duration and site are not player-editable in MVP.
4. Backend validates each proposed design revision and returns constraint status and derived estimates.
5. Host freezes a revision and requests simulation. Backend pins inputs, executes the engine and persists a completed or failed run.
6. Team reviews timeline, event log, resource curves, score breakdown and provenance. They may clone the design, change it and rerun.

## Frontend structure

Use feature-oriented folders: `features/briefing`, `design`, `catalog`, `simulation`, `collaboration`, `report`; shared `components`, `api`, `state`, `types`, `scene`, and `accessibility`. The advisor feature is deferred from MVP. Keep screens and presentational components separate from API clients. TypeScript types are generated or checked against the OpenAPI contract where practical.

Zustand holds transient view state, current draft and socket status. The backend-issued `design_revision` and validation response are canonical; optimistic edits are marked pending and reconciled with the response. Store only session identifiers client-side; avoid persistent sensitive mission data in local storage. TanStack Query is optional; avoid adding it if a small typed fetch wrapper suffices.

## Backend module boundaries

- `api`: REST and WebSocket transport, validation and response mapping.
- `identity`: bearer token verification, membership and role checks.
- `missions`: room, mission, design and revision lifecycle.
- `catalog`: immutable catalog versions and provenance metadata.
- `engineering`: pure modules for mass, power, energy, propulsion, data, communications, reliability and constraints.
- `simulation`: orchestrator, seeded event generation, timeline and output serialization.
- `scoring`: deterministic rubric and breakdown.
- `data_registry`: locally cached external data manifests and assets.
- `advisor`: optional future model adapter; suggestions only, no domain authority.

Domain modules should not import HTTP framework objects or issue database queries. Services coordinate pure calculations and repositories. Pydantic request/response models are API boundaries; domain models use explicit units and validated ranges.

## Source-of-truth ownership

| Information | Authority |
|---|---|
| Current membership/role and mission lifecycle | Backend + PostgreSQL transaction |
| Draft design and accepted revision number | Backend persistence; client submits intent |
| Catalog version | Backend catalog registry, immutable after publication |
| Validation, derived engineering metrics, score | Versioned backend calculation modules |
| Simulation run input/output | Immutable backend snapshot |
| Presence and cursor/typing | Ephemeral FastAPI WebSocket state only; excluded from durable events, idempotency hashes and room sequence |
| NASA source asset bytes and checksums | Versioned storage + manifest |
| 3D camera, selection highlight | Browser only |

## MVP non-functional targets

Planning targets to validate during build: four members total per room including host; 10 concurrent connected rooms for demo; design validation p95 below 500 ms; short run below 5 seconds for a 30-day coarse-step mission; report retrieval below 1 second. These are targets, not measured guarantees. One global simulation semaphore still permits only one active simulation across all rooms. Simulation time uses fixed steps/events and does not require one output row per real-world second.

## Error handling

Return stable error codes (`VALIDATION_FAILED`, `REVISION_CONFLICT`, `FORBIDDEN`, `RUN_NOT_READY`, `RATE_LIMITED`, `SIMULATION_BUSY`, `IDEMPOTENCY_KEY_REUSED`) with field-level details and a request ID. Never expose stack traces. Persist run failure state and diagnostic category, not secrets. WebSocket clients recover from disconnect by requesting current revision and run status over REST.

## Accessibility and educational clarity

Show units beside quantities; explain unavailable/unknown values; distinguish physical constraints from game score; include table and text alternatives for plots and 3D annotations. Every sourced or illustrative number links to its provenance record. Simulated failures are game events, not claims about real spacecraft failure rates.

## Final mission and deployment baseline

Each 3,600-second step is segmented at contact, instrument, observation, heater and mode boundaries; energy and data use actual active seconds. Camera exposure is an illustrative 60 seconds. The simulation-engine segment battery equations are authoritative. No protected battery reserve exists; 15% is scoring only. Only heater demand above the survival minimum may be curtailed. Unserved energy after that causes terminal simulated `POWER_BROWNOUT`; base bus, avionics, instruments, camera and radios are never shed. Heater curtailment with all remaining demand served is nonterminal degraded-power telemetry. MVP has no thermal-state solver; an unpowered survival minimum is recorded as secondary cause `THERMAL_SURVIVAL_UNPOWERED`, not a separate temperature-based failure.

**Primary scenario:** stationary Lunar Polar Robotic Lander intended to investigate one south-polar site through scheduled observations relevant to potential water ice. The actual site and dataset are **NOT YET APPROVED** under R1. Phases are launcher selection, simplified transfer, powered-descent budget check, and 30 landed simulated days. Launcher payload capacity/cost, transfer/descent requirements and site conditions are game parameters unless provenance says otherwise. This is educational and not flight-certified.

Run exactly 30 landed days (`2,592,000 s`) at a fixed one-hour (`3,600 s`) outer step: exactly 720 outer steps. Start at touchdown with an empty data store, component health 1.0, and battery at 80% of capacity (illustrative). Use SI units; capacities and energy in Wh, data in decimal MB, budget in credits. Illumination, contact, display-temperature, heater-demand and survival-minimum schedules are 720-entry versioned manifest fields, with sub-hour contact/operation intervals. Until validated source products are selected, they are explicitly illustrative.

Proposed mission procurement budget is 140 credits (illustrative). Sum component and launcher cost; exceedance is a hard design-feasibility failure, though a structurally valid design may still run to show consequences. Lander payload cap and budget are separate constraints.

MVP deploys as one Render FastAPI instance, Supabase PostgreSQL/Auth, Vercel static frontend and direct Three.js scene. FastAPI verifies Supabase JWT signature/JWKS, issuer, audience and expiry; it authorizes each action against mission membership/role. FastAPI WebSockets carry authoritative commands; Postgres revision checks and command IDs prevent silent overwrites. No Supabase Realtime, Redis, broker, microservices or worker process. Runs must finish within bounded instance execution; if they do not, reduce output density/scope rather than add infrastructure.

Operational states: `DESIGN → TRANSFER → DESCENT → LANDED_OPERATIONS → COMPLETE`, with terminal `FAILED`. Infeasible transfer/descent ends before landed simulation. Surface failures are reported with causes and score cap. Scores and engineering values come only from pinned backend versions.

Execution run status is separately constrained to `RUNNING → COMPLETED | FAILED`; no queued state. A valid simulated mission failure (including `POWER_BROWNOUT`) is still a `COMPLETED` engine run with `mission_success=false`, numeric score and mission phase `FAILED`. Infrastructure/engine failure is status `FAILED`, `score=null`, `mission_success=null`, and a `failure_code`. These statuses are terminal and align with the API/database enums. Results pin `score_formula_version=lander-score-v2` and `execution_profile_version=lander-exec-v1`; the science return denominator is expected data for the full pinned schedule, not actual data generated before termination. Cumulative downlinked data is bounded by generated and stored data.

Every accepted run uses the canonical `run_start` message in `API_SPECIFICATION.md`, validates revision UUID/mission/current revision number, and pins the exact immutable revision into the run input. Pin `score_formula_version=lander-score-v2` and `execution_profile_version=lander-exec-v1` with engine/ruleset/catalog/environment versions. Accepted retries resolve by command receipt and request hash before semaphore checks; genuinely new requests receive `SIMULATION_BUSY` without a run/receipt if the single-instance semaphore is occupied.

