# ORBITOPS — API Specification

Base prefix `/api/v1`. REST JSON over HTTPS; Supabase Auth JWT. FastAPI publishes OpenAPI. REST resource-creating POSTs require `Idempotency-Key`; WebSocket durable commands require UUID `command_id`. IDs are UUIDs except stable catalog/scenario identifiers. Units use SI unless explicitly named.

## REST endpoints

| Method and path | Purpose / authorization |
|---|---|
| `GET /scenarios` | List available scenario versions. |
| `GET /scenarios/{scenario_id}` | Briefing, goals, constraints and source/fidelity notes. |
| `GET /catalog?version={v}` | Immutable component catalog and provenance. |
| `POST /missions` | Create mission from scenario version and optional title; authenticated. Duration and site come from the pinned scenario manifest, not client input. |
| `GET /missions/{id}` | Mission metadata and caller role. Member. |
| `GET /missions/{id}/snapshot?after_sequence={n}` | Current canonical revision/run state and contiguous room events after sequence, or full snapshot when cursor is outside retention. Member recovery route. |
| `POST /missions/{id}/members/invitations` | MVP invite-token flow; owner/editor, rate-limited. External email delivery may be deferred; invite code can be copied. |
| `POST /invitations/accept` | Accept one-time invitation token in the authenticated JSON body; Idempotency-Key required; adds member only if room has fewer than four members total. |
| `GET /missions/{id}/design` | Current revision and validation. Member. |
| `POST /missions/{id}/design/validate` | Validate a proposed draft without committing; editor/owner. |
| `GET /runs/{run_id}` | Canonical status and terminal summary (no per-step progress stream in MVP). Member. |
| `GET /runs/{run_id}/report` | Full score, `score_formula_version`, execution profile version, score terms, timeline, metrics and provenance. Member. |
| `GET /runs/{run_id}/replay` | Return saved input snapshot and event stream; member. Does not recompute. |

## Representative schemas

`design_patch` WebSocket body: `command_id`, `expected_revision_no`, `patch` (JSON Merge Patch-like operations limited to known design paths). Server resolves IDs against catalog, applies field validation, computes estimates, commits revision. Response/event includes revision number, normalized design, validation issues, derived metrics and definition versions. Structurally valid but physically infeasible designs may be saved and flagged.

The canonical `run_start` JSON message is defined in the Final authentication, idempotency, revision and state contract below; it includes `type`, `command_id`, `design_revision_id`, `expected_revision_no`, and uint32 `seed`.

## WebSocket protocol

WebSocket authentication and connection sequence is defined in the Final Authentication Contract below. No bearer JWT appears in the URL and no mission data is sent before authorization.

Client commands, canonical schema, ordering and replay are defined in the Final Authentication and RunStart Contracts below. Presence is ephemeral, not sequenced durably.

## Error contract

```json
{"error":{"code":"REVISION_CONFLICT","message":"Design changed; reload current revision.","request_id":"…","details":{"current_revision_no":7}}}
```

Do not return internal exception text, SQL, tokens, or model prompts. `401` missing/invalid identity, `403` insufficient role, `404` unknown or undisclosed resource (including invalid invite token), `409` conflict/idempotency mismatch/`ROOM_FULL`/`INVITATION_ALREADY_USED`, `422` schema/engineering validation, `429` rate limit or `SIMULATION_BUSY`, `5xx` generic with request ID.

## Versioning and design notes

Breaking payload changes require a new API version or explicit schema evolution. REST is used for reads, catalog, reports and recovery; authorized REST resource creation uses Idempotency-Key. FastAPI WebSockets are the authoritative path for design and run commands.

## Final MVP API contract changes

FastAPI is the authoritative multiplayer endpoint; Supabase Realtime is not used. For every browser socket, the first frame must contain the Supabase JWT; FastAPI verifies signature, issuer, audience and expiry, then authorizes membership/role before hello or mission data. Never put bearer JWT in URLs.

WebSocket schemas and authentication order are defined in the Final Authentication and RunStart Contracts below; all durable room commands are committed before broadcast.

The canonical JSON RunStart schema is defined below and is shared by all documents.

## Final command, revision and reconnect semantics

PostgreSQL is the durable authority. FastAPI owns every write; Supabase Realtime is excluded. Reads/catalog/reports/recovery use REST; FastAPI WebSockets carry collaboration commands. A client command contains UUID `command_id`, mission ID from socket route, actor from verified JWT, and `expected_revision_no` for design changes. After authentication and role authorization, ordinary commands validate schema, then check idempotency before revision compare-and-swap. `run_start` follows its stricter contract below: check an existing receipt/hash before revision freshness or semaphore checks, then validate revision only for a new command. A transaction inserts command receipt, appends immutable revision (if applicable), increments `missions.room_sequence`, writes durable event and stores command outcome. Broadcast occurs only after commit. Same command ID and same hash returns saved outcome; same ID with a different hash returns `409 IDEMPOTENCY_KEY_REUSED`. Stale revision returns `409 REVISION_CONFLICT` with current revision; it produces no revision event.

Room sequence is one strictly increasing integer per mission, assigned atomically with the durable event in the same transaction. On connect, client sends last seen sequence. Subscribe to the process-local mission queue first and buffer frames; then read the cursor, events and snapshot in one repeatable-read transaction. Replay retained events only if contiguous and cursor is within bounds; otherwise return a full `snapshot` containing current design revision, mission/run state and captured sequence. Discard buffered live frames at/below that sequence and merge later frames in sequence order. If commit succeeds but broadcast fails, reconnect reads the durable event. Client applies each sequence once and requests resync on any gap; presence is ephemeral and not sequenced durably. In one backend instance, per-mission async locks reduce contention, but correctness comes from PostgreSQL unique keys and compare-and-swap. Concurrent run starts are idempotent per command and only one run may be active per mission. REST recovery endpoints return the same canonical revision/run state as socket snapshot.

At startup, before serving REST or accepting sockets, recover stale `RUNNING` rows and purge expired REST idempotency receipts, room events and diagnostic details. A single lightweight in-process daily maintenance task repeats expiry purges; it is not a separate worker/service. Snapshot fallback remains authoritative after event purge. If host timeout/restart interrupts a run, mark it `FAILED`, with `failure_code=BACKEND_RESTARTED`, `score=null`, `mission_success=null` and no partial result; never leave it indefinitely active or claim partial completion. Configured time/output bounds produce `status=FAILED` and `failure_code=SIMULATION_LIMIT`. A failed run is never resumed; a new attempt requires a new `command_id` and a valid current design revision.

Implementation boundary: after run/receipt/event commit, send `command_accepted` and launch one tracked in-process asyncio task that executes the bounded CPU loop through FastAPI's threadpool; return the WebSocket reader to its receive loop. An in-process semaphore limits active simulations globally to one; there is no queue, broker or worker. If task scheduling fails after acceptance, persist `FAILED/ENGINE_ERROR`. Engine exceptions persist `FAILED/ENGINE_ERROR`; final report/hash/status/terminal event commit atomically before broadcast. Release the semaphore only after terminal persistence. If terminal persistence fails, retry the DB transaction up to three times; after three failures, mark run service unhealthy, retain the semaphore and fail closed to all new run starts until operator restart. Startup recovery then marks the stale row `FAILED/BACKEND_RESTARTED` if terminal persistence still cannot be completed. If the semaphore is occupied, a genuinely new run start receives `429 SIMULATION_BUSY` with retry guidance and creates no run or receipt. REST `GET /runs/{id}` exposes the same canonical state. If measured execution exceeds the host limit, reduce scenario/output rather than add a worker.

## Final authentication, idempotency, revision and state contract

**WebSocket connection order:** (1) establish socket; (2) first client frame must be `{"type":"authenticate","jwt":"<Supabase access JWT>"}` within the 5-second authentication timeout; (3) verify JWT signature against configured Supabase JWKS, issuer, audience, `sub` and expiry; (4) authorize mission membership and role; (5) only then accept `{"type":"hello","last_seen_sequence":N}`; (6) send snapshot or contiguous event replay. Cache JWKS for at most 5 minutes; refresh once for an unknown `kid`; fail closed when no valid cached/fetched key is available. Before step 4 succeeds, server sends no mission data, events, member list, or detailed errors. Recheck token expiry and current mission membership/role for every durable command; revoked membership closes/rejects the command. Enforce configured origin allowlist, maximum 64 KiB inbound frame, 10 durable commands/second/user and 10 presence updates/second/connection; reject excess with stable rate-limit behavior. Use generic auth failures and never log JWT frames. Invalid auth closes with a generic policy close.

**Canonical run command used everywhere:**

```json
{
  "type": "run_start",
  "command_id": "uuid",
  "design_revision_id": "uuid",
  "expected_revision_no": 7,
  "seed": 20261112
}
```

For a genuinely new command, the server verifies the referenced revision exists, belongs to the mission in the socket route, has `revision_no == expected_revision_no`, and equals the mission's current revision. Otherwise return `REVISION_CONFLICT` and create no run. The accepted immutable revision and its resolved components are copied into the frozen input snapshot with seed and all version IDs. An already accepted command ID is resolved by receipt/hash first and returns its original outcome even if the mission has advanced to a newer revision.

**WebSocket command idempotency and semaphore order:** authenticate/authorize, acquire an in-process per-command lock, then read `(mission_id,command_id)` receipt before treating a request as new or checking the simulation semaphore. Hash normalized command type, mission, actor and payload excluding `command_id`. Existing receipt with equal hash returns its original outcome/run ID immediately even if semaphore is occupied or revision has advanced; different hash returns `IDEMPOTENCY_KEY_REUSED`. For a new key, validate revision association/current number, then nonblocking-acquire global semaphore; if busy, return `SIMULATION_BUSY` and do not insert receipt/run. Once acquired, transactionally insert unique command receipt, run row and first durable room event. If simultaneous duplicates race, unique-key loser releases any acquired semaphore, reloads receipt and returns same outcome or hash conflict. Release after terminal persistence. Presence has no command ID/hash/receipt/sequence and is ephemeral.

**REST `Idempotency-Key`:** required for resource-creating POSTs (`POST /missions`, invitation creation and invitation acceptance). Scope key to authenticated user + method + normalized path; hash canonical JSON body excluding the key. Canonical `orbitops-cjson-v1` is normalized schema JSON serialized by the pinned Python backend as UTF-8 with sorted object keys, no insignificant whitespace, finite numbers only, negative zero normalized to zero, and the pinned runtime's shortest round-trip float representation; hash is SHA-256. Same key/hash returns original status and resource/response; changed hash returns `409 IDEMPOTENCY_KEY_REUSED`. In one DB transaction, serialize on the unique scope, check any receipt, create/accept the resource and insert its final response receipt; both commit or both roll back. Persist receipts only with a successful resource mutation; validation, rate-limit and `ROOM_FULL` responses roll back and do not consume the key. Unique `(user_id,method,path,key)` is the race guard; a losing concurrent request reads and returns the committed receipt. Store REST receipts for 24 hours; retries after expiry are outside the idempotency guarantee. Reads and non-mutating validation do not use a key. WebSocket uses the same canonicalizer with `command_id`, scoped to mission/actor/type. Retain WebSocket receipts for the mission/run retention lifetime. REST and WebSocket receipts are separate namespaces. Presence is excluded from both.

**Invite token contract:** invitation creation makes a random UUID and derives an unpredictable one-time token as `invitation_id.key_version.base64url(HMAC-SHA256(server_secret, "orbitops-invite-v1|"+invitation_id+"|"+expires_at_epoch+"|"+key_version))`. `expires_at_epoch` is an integer Unix timestamp in UTC aligned to seconds and stored at second precision. The HMAC key is a backend secret; `key_version` selects it. Store only SHA-256 of the full token plus key version; never store/log the plaintext token. Retain old HMAC keys until all tokens under that version expire. Token expires after 24 hours and can be revoked. Limit genuinely new invitation creations to 5 per owner per mission per hour; first resolve an existing same-key REST receipt, which does not count against the limit. A rate-limited new request creates no invitation or receipt and may be retried after the window. Invite role is `viewer` or `editor`; an editor may invite viewers only, while an owner may invite either. Acceptance requires an authenticated user and `Idempotency-Key`, and the token is sent in the JSON body (never URL/query/log). In one transaction, lock the mission row, verify HMAC in constant time, check stored token hash/expiry/revocation/use and current membership, then insert membership and mark invitation accepted. Room capacity is four total members including owner; a full room returns `ROOM_FULL` without consuming the invite. Concurrent acceptances serialize on the mission row; only one may occupy the last slot. Same acceptance key/hash replays its original response; because the token is deterministically rederived from invitation ID, expiry and retained key version, replay returns the original code without storing plaintext. A used token with a different key/user returns `INVITATION_ALREADY_USED`.

**Run status machine:** durable execution `RUNNING → COMPLETED | FAILED`; there is no queued state. `COMPLETED` means engine produced a complete valid report, whether `mission_success` is true or false (pre-touchdown infeasibility has score 0; simulated landed failure has capped score). A simulated terminal code such as `POWER_BROWNOUT` is returned as `result_json.mission_failure_code`, with `failure_code=null`, numeric `score`, and `mission_success=false`. `FAILED` is infrastructure/engine termination with `score=null`, `mission_success=null`, `result_json=null`, and technical `failure_code` such as `SIMULATION_LIMIT`, `BACKEND_RESTARTED`, or `ENGINE_ERROR`. `COMPLETED` and `FAILED` are terminal. Mission phase is separately `DESIGN → TRANSFER → DESCENT → LANDED_OPERATIONS → COMPLETE` or `FAILED`. API `run_status` and DB `status` use the same execution-state enum; technical failure details use `failure_code`, not composite status strings.

