# ORBITOPS — Testing Strategy

Testing is a required implementation activity, though this planning task does not execute tests or add application code.

## Test layers

1. **Schema/unit:** Pydantic bounds, units, catalog provenance, pure engineering formulas, constraint margins, score normalization, PRNG and canonical serialization.
2. **Property/invariant:** energy never appears without generation, battery stays within bounds, mass is nonnegative, storage does not exceed capacity without overflow event, delivered data never exceeds stored/generated data, no duplicate event sequences, score remains in defined bounds.
3. **Determinism:** identical snapshot + seed + versions yields same event ordering and canonical result; different seeds affect only stochastic event streams; changing catalog version changes input fingerprint.
4. **Integration:** Postgres migrations, RLS/member roles, revision conflict, idempotent run creation, state transitions, result persistence and API schemas.
5. **WebSocket:** auth/role checks, duplicate commands, ordering, gap recovery, reconnect snapshot and ephemeral presence throttling.
6. **Frontend:** feature-level interaction, backend error states, responsive/accessibility checks, clear source-value labels; 3D scene visual checks.
7. **End-to-end:** briefing → create/edit design → validate → run → report → clone/replay, solo and collaborative paths.
8. **Operational:** deployment smoke, health/readiness, migration procedure, secrets check, backup/restore rehearsal as scope allows.

## Scientific and numeric validation

Maintain test vectors for formulas with hand-computed cases. Validate units at boundaries and test zero/edge cases. Provenance links and source version metadata are checked for every `sourced` value. Illustrative data is checked to have an explicit label. Do not treat agreement with an illustrative game output as scientific validation. Any sourced model should be independently reviewed against the cited document and its applicability limits.

## Security and abuse tests

Test mission membership isolation, role matrix, cross-room WebSocket subscription denial, payload size/rate limits, injection-safe strings, invite token entropy/expiry, unauthorized run/report access, and absence of service credentials in built client assets. Fuzz malformed catalog/design inputs and verify stable errors rather than crashes.

## Golden runs and regression

Keep a tiny set of versioned golden mission snapshots and expected summaries, input hashes and event sequences. Any intentional model/ruleset change bumps version and updates review notes; do not silently rewrite historical outputs. Use numeric tolerances only where appropriate and compare exact discrete event ordering separately.

## MVP acceptance criteria

- Same pinned inputs and seed reproduce a run under the declared policy.
- UI never labels estimates as backend final results before server response.
- Every failed constraint and score contribution is explainable.
- A disconnected client can recover to authoritative room revision/run status.
- NASA network outage does not prevent gameplay.
- Reports identify model fidelity, source links and illustrative settings.

## Final lander MVP acceptance checks

- Exactly 30 days and 720 one-hour landed steps; transfer/descent phases separately evaluated.
- Launcher payload includes spacecraft plus explicit propellant before separation and excludes launcher hardware mass.
- Same input snapshot, seed and pinned versions yield identical event order/result hash in pinned runtime; cross-runtime floating metrics use documented tolerances.
- Energy cannot appear without generation; battery is bounded; brownout is explicit; data overflow/drop and contact-capacity bounds are tested.
- Zero sunlight, zero battery, no contact, full store, no science load and simultaneous events have expected deterministic results.
- Two simultaneous patches against same revision yield one accepted change and one conflict. Duplicate command returns same outcome. Reconnect/gap returns replay or snapshot.
- Invalid JWT claims/signature, expired token, role denial and cross-room subscription fail closed.
- Frontend contract types agree with OpenAPI/Pydantic REST and WebSocket schemas.
- Public NASA outage does not prevent run; illustrative environmental schedule is labeled as such.
- Mission-ending failure caps score at 49.9; pre-touchdown infeasibility scores 0; every score term is inspectable.

## Final consistency test vectors

Use the hand-calculated battery vectors and mass/propellant vectors in [SIMULATION_ENGINE_SPEC.md](SIMULATION_ENGINE_SPEC.md) as golden unit tests. Include exact checks for gross generated/consumed Wh, end battery Wh, unserved and wasted Wh; no negative solar generation; and no double count of propellant. Score tests cover zero denominators, missing telemetry, no valid opportunities, no random recovery event, pre-touchdown failure, landed terminal failure cap, and perfect success.

Run all 720 steps twice with same canonical snapshot, seed, PRNG/runtime and versions; compare ordered event IDs and result hash exactly. Verify step-order fixtures for degradation/event/observation/downlink/overflow/failure/scoring. Check compact result-size limit, terminal `FAILED` with `failure_code=SIMULATION_LIMIT`, and stale-run recovery after simulated restart. Multiplayer contract tests assert duplicate command same outcome, command ID changed payload rejection, stale revision conflict without event, commit-before-broadcast, contiguous replay, snapshot fallback after retention, sequence gap recovery, two-writer race, and only one active run.

Also assert only one simulation acquires the process semaphore at once; a concurrent request returns `429 SIMULATION_BUSY` without entering an unbounded queue. A busy response must not create a run row or consume the idempotency key.

## Final API, partial-window and idempotency contract cases

- Partial 600-second high-rate contact delivers at most `.025 MB/s×600=15 MB`, and radio energy is `24 W×600/3600=4 Wh`; it is not charged or credited as a full hour.
- Neutron instrument active for 900 seconds at `.5` duty over a 1,800-second eligible interval runs 900 seconds, produces `.8 MB/h×900/3600=.2 MB`, and consumes `28 W×900/3600=7 Wh`.
- A scheduled camera exposure uses exactly 60 seconds, `12 W×60/3600=.2 Wh`, and produces 2 MB only if continuously powered through the interval; terminal segment brownout makes it missed and yields zero data. Camera is never a load-shedding candidate.
- A 900-second 45 W heater interval consumes 11.25 Wh. Partial radio contact has proportional downlink capacity; data created in a segment cannot be downlinked until a later segment.
- A 900-second 25%-duty neutron interval uses 900 active seconds, consumes `28×900/3600=7 Wh`, and generates `.8×900/3600=.2 MB`. A 900-second low-rate radio contact consumes `10×900/3600=2.5 Wh` and has at most `.005×900=4.5 MB` capacity; if segment-start buffer is 3 MB, it downlinks 3 MB only and same-segment science generation is deferred.
- Segment battery golden vectors exactly match the worked 900 s charge, 600 s discharge, full-capacity clipping, 300 s depletion, zero-light/zero-battery, heater-excess-only curtailment, and post-curtailment unserved vectors in the engine specification. Assert bus, battery-state, load-demand and waste conservation independently to `1e-9 Wh`; include `C=0`, `η_c/η_d` boundaries, and `G=0`.
- A terminal brownout segment records supply, actual consumed energy and unserved demand separately, preserves `E_load=E_consumed+E_unserved`, credits zero scheduled operations in that failed segment, and creates zero science data/downlink there. No later segment executes.
- Cumulative science downlink never exceeds cumulative science generation or segment-start stored science data; overflow is lost. A completed camera observation adds exactly 2 MB once; an incomplete observation adds zero and no continuous camera rate.
- A fully powered observation is valid only if its complete expected payload is stored. If a 2 MB camera payload cannot fit, mark it invalid, count generated/overflow bytes correctly and award no objective/observation credit; continuous observation payload must also be fully stored for science credit.
- Minimum catalog cost is exactly `18+16+14+12+24+9+9+6+10=118` credits; budget cap remains 140 with 22 credits remaining.
- The minimum catalog build dry mass is exactly 290 kg; adding 360 kg propellant once gives 650 kg payload, below the illustrative 900 kg light-launcher cap.
- Force battery projection below zero at a segment boundary: assert only heater demand above survival minimum is shed, then recomputed; instruments, camera, radios, base bus and avionics are never shed. If any load remains unserved after permitted curtailment, assert simulated terminal `POWER_BROWNOUT`, zero credited powered seconds for that segment's operations, incomplete observation/contact, and no reserve cutoff at 15%. When survival-minimum heater energy is among unserved loads, assert secondary cause `THERMAL_SURVIVAL_UNPOWERED`; do not simulate a separate temperature-based failure because MVP defines no thermal state equation. Heater curtailment with all remaining loads served is degraded-power telemetry but is not terminal.
- WebSocket order: connect → authenticate first frame → verify signature/issuer/audience/expiry → authorize mission role → hello → snapshot/replay. Assert zero mission messages before authentication and for every invalid/unauthorized step.
- REST snapshot recovery returns the same canonical revision, room sequence and run state as the WebSocket snapshot; retained contiguous events or snapshot fallback match reconnect behavior.
- RunStart contract rejects missing/extra or wrongly typed fields; stale revision, revision from another mission, and revision number mismatch fail before run creation. Accepted run snapshot pins exact revision ID and content.
- Retry accepted `run_start` with same command ID/hash while semaphore is occupied returns the original run ID/outcome. Same ID with changed payload returns `IDEMPOTENCY_KEY_REUSED`.
- Two simultaneous identical `run_start` commands result in one run row/event and identical outcome to both callers. A genuinely new command while busy returns `SIMULATION_BUSY`, creates no receipt/run, and may be retried after release.
- New `run_start` with a revision from another mission, stale `expected_revision_no`, or no-longer-current revision returns `REVISION_CONFLICT` before semaphore acquisition and creates no receipt/run. An already accepted same-hash command still returns its original outcome when the mission revision has since advanced.
- REST Idempotency-Key same user/path/key/hash concurrent requests create one resource and replay its stored response; changed hash conflicts. Presence never creates a receipt, room sequence, durable event or replay entry.
- Run status transitions allow only `RUNNING→COMPLETED` or `RUNNING→FAILED`; terminal states cannot transition. Mission failure with a valid score is `COMPLETED` plus `mission_success=false`; infrastructure failure is `FAILED` with null score/failure code.
- Score denominator golden cases: full pinned schedule expects 100 MB, successful run downs 80 MB → return fraction .80; early terminal failure downs only its 20 MB generated but denominator remains 100 MB → .20; successful run downs 100 MB → 1.0. Denominator is invariant under terminal time and the result pins `lander-score-v2`.
- Assert `expected_science_data_mb` is computed and stored in immutable `input_snapshot` before engine-task dispatch; mutate later schedule/catalog versions and verify the run denominator does not change.
- Score arithmetic vector: 2 objectives/1 achieved, 8 observations/2 complete, 100 MB expected/20 MB downlinked gives `A=.3525`; with `F=1,E=.5,R=.25,O=.25`, raw score `50.575` is capped to `49.9` for landed failure. Pre-touchdown hard-gate failure is exactly score 0; perfect success is 100.0. Brownout is a simulated mission failure (`COMPLETED`, `mission_success=false`, numeric score), not technical `FAILED`.
- Propulsion regression recomputes with full precision: `g0=9.80665`, `Isp=300 s`, dry mass 295 kg, propellant 360 kg gives transfer consumption 138.693050 kg, descent consumption 184.4100 kg, residual 36.8969 kg and landing mass 331.8969 kg; 180 kg initial propellant provides only 701.388 m/s for descent after transfer and yields `DESCENT_PROPELLANT_SHORTFALL`.
- A completed simulated failure has a valid numeric score and `mission_success=false`; an infrastructure `FAILED` run has `score=null`, `mission_success=null`, no partial result, and a failure code.
- Database integrity tests reject a run referencing another mission's revision, a revision whose parent belongs to another mission, itself or a non-earlier revision, duplicate concurrent revision numbers, unknown catalog/environment versions, mutation/deletion of revisions/published catalog/completed runs, and deletion of referenced versions.
- Concurrency/integrity tests race two revision inserts at the same expected number (one commit, one conflict), race same-mission run inserts (one active row), reject cross-mission room receipt/event references, and verify `RUNNING` can make only one terminal transition. Test draft→published catalog publication once and reject all later catalog/manifest mutation using the runtime role.
- Inject transaction failures between room-sequence increment/event insert and between run/receipt creation; assert rollback leaves no sequence gap, event, receipt or orphan run and releases the semaphore. Inject a post-commit/pre-broadcast disconnect and assert reconnect replays the committed event once.
- WebSocket security tests send no-auth/expired/wrong-issuer/wrong-audience frames and revoked membership; assert no mission payload arrives before auth and every durable command rechecks current role. Test token frame redaction, origin allowlist and size/rate bounds.
- Startup recovery marks stale RUNNING rows FAILED with `BACKEND_RESTARTED`, null score/mission_success/result, and redacted diagnostic. Verify diagnostic purges after 30 days while run snapshot/failure record remains.
- After room events older than 7 days are purged, reconnect from an expired sequence returns a transactionally consistent full snapshot and continues from its captured room sequence without a gap.
- Startup and once-daily in-process retention purge remove REST receipts after 24 hours, room events after 7 days and diagnostic details after 30 days; verify command receipts/run snapshots remain and snapshot fallback works after purge.
- Force an event commit between socket subscription and snapshot read; assert buffered/replayed sequence merge delivers it exactly once. Force commit-before-broadcast process interruption; reconnect must recover the committed event from Postgres.
- Four authenticated collaborators can join one mission; a fifth is rejected by the documented room capacity policy. Each command rechecks role after connection establishment.
- Race two valid invite acceptances for the fourth room slot; exactly one member is inserted, count remains four, the losing transaction returns `ROOM_FULL` without consuming its invitation. Token plaintext must not appear in DB fields or logs; idempotent invite response reconstructs the same token from invitation ID/key version.
- Enforce 64 KiB incoming WebSocket frame size, 10 durable commands/second/user, 10 presence updates/second/connection and 5 invite creations/hour/owner/mission; excess traffic is rejected without a durable command receipt or sequence increment.
- REST invite validation/rate-limit/`ROOM_FULL` failures leave no idempotency receipt; a successful same-key invitation replay returns the same reconstructed token even after the creation rate window is exhausted.
- Battery rule regression asserts only heater demand above survival minimum is shed; science, camera, radio, base bus and avionics are never shed. Older full-hour shorthand is not used.
- `THERMAL_LOAD_SPIKE` adds 20 W heater request without changing survival minimum; demand above component limit is capped only for this event, excess is reported as `heater_capacity_shortfall_w`, and no fictitious draw or separate temperature failure is produced.

