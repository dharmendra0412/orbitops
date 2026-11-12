# ORBITOPS — Technical Decisions and Open Questions

**Disposition:** Technical contracts are consolidated; human approval remains pending for the explicit gates below. This document is not flight certification or approval to silently choose scientific inputs.

## Decision record

| ID | Decision | Why | Alternatives / trade-off |
|---|---|---|---|
| TD-01 | Modular monolith for MVP | One deployable backend, transactions and direct debugging; module seams preserve future extraction. | Microservices add networking, deployment and observability burden. |
| TD-02 | Backend is authoritative | Prevents tampered or divergent mission results and provides one reproducible record. | Browser previews may show non-authoritative UI estimates only if clearly labeled; simplest MVP is server-derived estimates. |
| TD-03 | REST reads/recovery plus authoritative FastAPI WebSocket collaboration commands | Durable edits commit to Postgres before broadcast; sequence and idempotency support recovery. | Supabase Realtime adds a second authority; polling is less responsive. |
| TD-04 | Immutable catalog, design revision and run snapshots | Supports audit, replay and reproducibility despite later edits. | Mutable rows are simpler initially but corrupt historical meaning. |
| TD-05 | Relational Postgres with selective JSONB | Strong relationships and constraints with flexible versioned snapshots. | Fully normalized metric histories can be costly; pure JSON weakens query integrity. |
| TD-06 | Coarse deterministic simulation | Meaningful resource coupling at hackathon scope, fast and inspectable. | High fidelity is infeasible without extensive validated data and verification. |
| TD-07 | Scenario-cached NASA data | Stable offline demo and stable historical runs. | Live API creates outages, rate limits and changed answers. |
| TD-08 | Direct Three.js for visual context | Fits scene need without extra React renderer abstraction; 3D stays separate from truth. | 2D-only is simpler; R3F can be revisited later. |
| TD-09 | AI advisor is optional and advisory | Adds educational explanations while leaving physics, validation and score deterministic. | No AI is safer for scope; autonomous design is explicitly out of scope. |
| TD-10 | Every number has provenance class | Prevents illustrative game-balance values from being mistaken for NASA facts. | Free-form prose alone is harder to audit and render consistently. |

## Proposed implementation stack

Retain React, TypeScript, Vite, Tailwind, direct Three.js, Zustand, Python/FastAPI, NumPy, Pydantic, WebSockets, Supabase/PostgreSQL, Vercel and Render. Keep dependency count modest. A tracked in-process task runs the bounded engine through FastAPI's threadpool under one global semaphore; it is not a separate worker or queue. If measured run duration exceeds host budget, reduce output density/scope before considering any infrastructure change.

## Human decisions required before implementation

These are explicit approval gates; none is treated as an engineering fact or silently defaulted.

1. **R1 — Named site and data:** Select the single named lunar polar site and approve the cached dataset/transform, or approve an explicitly illustrative schedule until curation is complete. `south_pole_site_a` is only a schema placeholder.
2. **R2 — Game parameters:** Confirm that the 18 catalog values, event probabilities/impacts, environment heater/illumination/contact schedules, 700/1,300 m/s propulsion requirements, 300 s Isp and 360 kg propellant are permitted as illustrative game parameters. Any sourced value requires domain review and citation before being labeled sourced.
3. **R3 — Scoring:** Approve `lander-score-v2` weights, hard gates, normalization targets and the 49.9 terminal-mission-failure cap.
4. **R4 — Collaboration and demo:** Approve four-member limit, Supabase-authenticated demo, copied one-time invite token, editor/viewer role policy and one-instance Render deployment expectations.
5. **R5 — Execution budget:** Benchmark the 720-step engine on the selected Render instance and approve or revise provisional `lander-exec-v1` 5-second wall deadline, 100-event cap and 2 MB result cap. These execution limits are not flight/science parameters; a wall deadline can make status host-load dependent.
6. **R6 — Event requirements:** Confirm event deadline, hackathon team capacity, UI currency label and accessibility/language requirements. These do not alter the physics contract but affect implementation planning and submission readiness.

## Known risks

- Scientific simplifications can be overinterpreted unless reports label model limits and provenance.
- Four-player concurrent edits can conflict; optimistic revisions and reconnect snapshots are mandatory.
- Browser/Render execution limits may constrain the bounded in-process run; reduce output density/scope before considering new infrastructure.
- Optional Three.js scene can consume time without improving the core loop; build after design/run/report.
- Supabase Auth, RLS, backend bearer verification and WebSocket identity must be configured consistently.
- Strict floating-point bit-for-bit determinism across platforms is difficult; pin runtime and versions, define tolerance policy, and retain output snapshots.

## Finalization change log (2026-11-12)

| Decision | Change | Reason |
|---|---|---|
| Mission | Resolve former ambiguity to stationary Lunar Polar Robotic Lander. | Makes launcher, descent and surface operation dependencies concrete. |
| Deployment | One FastAPI instance; remove microservices, worker, broker and Redis from MVP. | Avoid unneeded operations. |
| Sync | FastAPI WebSockets become authoritative command path, backed by PostgreSQL revision/sequence/idempotency checks. Remove Supabase Realtime. | One write authority and clear reconnection model. |
| Auth | Supabase Auth JWT verified in backend via JWKS/signature, issuer, audience and expiry; role/member check each action. | Authentication alone does not grant mission access. |
| Rendering | Direct Three.js rather than React Three Fiber. | Lower abstraction/dependency surface; scene remains non-authoritative. |
| Simulation | 30 days, fixed 3,600-second step, 720 updates; fixed phases and versioned rules/data/catalog. | Reproducible scope and bounded runtime. |
| Catalog/score | Proposed illustrative 18-item catalog and transparent five-term formula with feasibility gate. | Explicitly teach trade-offs without inventing NASA specifications. |
| AI | Defer advisor from MVP. | Keeps core build deterministic and removes provider/privacy dependency. |

Prior modular-monolith, relational PostgreSQL, immutable run snapshots, cached NASA inputs and backend-authoritative engineering decisions remain valid. Human approval is still pending for the named site/schedule, proposed game values, score weights, collaboration priority and one-hour fidelity. Do not silently treat these as approved.

## Consistency corrections included in this documentation set

- Canonical energy uses W × seconds / 3600 for Wh; battery flows report generated, consumed, stored, unserved and wasted quantities separately, with explicit efficiency, clipping, shedding and failure rules.
- Propulsion is one shared abstract budget and one engine model for sequential transfer/descent burns; propellant is counted once.
- Catalog generation is positive rated W, separate from draw; data rates carry explicit units; all numeric properties require provenance class.
- Scenario defaults are normalized to 700 m/s transfer, 1,300 m/s descent, 360 kg illustrative propellant and 140-credit budget.
- Score terms define numerator/denominator/zero/missing behavior, mission-completion evaluation and worked examples.
- Socket command transaction, idempotency, revision conflict, room sequence and reconnect replay/snapshot semantics are aligned across API and DB specs.
- Partial windows subdivide each one-hour step at schedule boundaries; all energy/data use actual powered seconds, with no protected battery reserve.
- RunStart retries resolve receipt/hash before semaphore; only new busy requests are rejected without receipt. WebSocket authentication precedes hello and all room data.
- Minimum catalog build is 118 credits; budget cap is 140.
- Segment battery branches specify Wh from actual integer seconds, with separate battery state/bus/load conservation, efficiency loss, capacity clipping, zero-capacity behavior, heater curtailment and terminal unserved-energy vectors.
- MVP has no thermal state equation. Unpowered survival-minimum heat is reported as secondary mission failure cause `THERMAL_SURVIVAL_UNPOWERED` under simulated `POWER_BROWNOUT`.
- Database schema uses `BIGINT` for the uint32 seed range, with a CHECK constraint enforcing `0..4,294,967,295`.
- `F` in `lander-score-v2` means pre-touchdown hard-gate feasibility. A later landed failure does not retroactively change `F`; the overall score is capped at 49.9.

## Detailed audit history carried forward from the audited outputs version

This record preserves the detailed prior audit decisions; it does not close the human approval gates above.

- Canonical energy uses W × seconds / 3600 for Wh; battery flows report generated, consumed, stored, unserved and wasted quantities separately, with explicit efficiency, clipping, heater curtailment and failure rules.
- Propulsion is one shared abstract budget and one engine model for sequential transfer/descent burns; launcher payload includes propellant exactly once and catalog hardware mass excludes propellant.
- Catalog generation is positive rated W, separate from draw; data rates carry explicit units; every numeric property has a provenance class.
- Scenario defaults are 700 m/s transfer, 1,300 m/s descent, 360 kg illustrative propellant and a 140-credit budget. These are game settings, not NASA data.
- Score terms define numerator, denominator, zero/missing behavior, mission-completion evaluation and worked examples.
- Socket command transaction, idempotency, revision conflict, room sequence and reconnect replay/snapshot semantics are documented across API and database specifications.
- Partial windows subdivide each one-hour step at schedule boundaries; energy and data use actual powered seconds; no protected battery reserve is defined.
- Accepted `run_start` retries resolve receipt/request hash before semaphore checks; a genuinely new busy request creates no run or receipt. WebSocket authentication precedes hello and room data.
- Minimum catalog build is 118 credits; budget remains 140 credits.
- Segment battery branches specify actual integer-second Wh, battery/bus/load conservation, efficiency loss, capacity clipping, zero-capacity behavior, heater curtailment and terminal unserved-energy vectors.
- The unsupported two-step temperature-failure rule was removed. MVP has no thermal state equation; unpowered survival-minimum heat is a secondary `THERMAL_SURVIVAL_UNPOWERED` cause under simulated `POWER_BROWNOUT`.
- Sample design uses catalog ID `solar_fixed_80` and version `lander-mvp-1`; quantity limits, unit semantics and event-model references cover all 18 entries.
- Database rules specify immutable revisions/catalog/manifests/run inputs, legal state transitions, concurrent revision allocation, receipt-to-run references, transaction rollback and reconnect queue/snapshot race handling.
- The science data-return denominator is fixed to the complete pinned schedule; downlink is bounded by segment-start stored science data and generated data.
- Seed storage is `BIGINT` with the uint32 range CHECK. In `lander-score-v2`, `F` is pre-touchdown feasibility; a later landed failure does not change `F`, and the final score is capped at 49.9.
