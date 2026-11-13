# ORBITOPS Engineering Status

**Snapshot date:** 2026-11-13  
**Branch:** feature/spice-kernel-provenance  
**Product scope:** Multi-planetary mission engineering foundation  
**Status:** Mission workspaces, verification evidence capture, and spacecraft configuration/budget services, and requirement-to-component traceability, and model verification/validation evidence governance, and historical revision change-impact analysis, and frontend checksum-to-manifest registration workflow, and consolidated mission review package, and project-scoped dataset/model evidence associations, two-body Keplerian orbital mechanics prototypes, bounded PDS4 XML label inspection, and deterministic JPL-DE440-based orbital regression benchmarks implemented; independent engineering acceptance remains pending.

## Implemented

- FastAPI + React/TypeScript/Vite application foundation.
- Engineering value contracts with units, dimensional checks, provenance classes,
  credibility status, equation/model references, intended use and limitations.
- Dataset manifest validation and immutable SQLite metadata registry.
- SHA-256 file inspection with a 100 MiB limit; uploaded file bytes are not persisted.
- Frontend dataset registration workflow that uses the inspected checksum to create source manifests and browse registered dataset metadata.
- Consolidated project review package endpoint and frontend JSON export for mission revision, spacecraft configuration, budgets, traceability, requirement verification evidence, and project-linked dataset/model assessment records.
- Append-only project evidence links that associate existing dataset manifests and model assessment records with mission projects.
- SQLite model-run snapshots preserving inputs, outputs, model/equation IDs,
  assumptions, limitations and UTC run time.
- Ideal Tsiolkovsky rocket-equation delta-v prototype (UNVALIDATED).
- Constant-average-power energy-balance prototype (UNVALIDATED).
- Eight-planet destination taxonomy and seven mission archetypes through
  GET /api/v1/missions/catalog.
- Persistent mission project workspaces with typed requirements, immutable numbered revisions, retrieval and pagination.
- Append-only requirement verification evidence registry linked to requirements in the latest project revision, with verification-method consistency checks.
- Spacecraft component contracts with subsystem classification and provenance-aware mass/power values.
- Append-only spacecraft configuration revisions associated with a mission project.
- Append-only requirement-to-component allocations validated against the latest mission and spacecraft revisions.
- Latest-revision traceability matrix with unallocated requirement counts, stale component references, and verification evidence outcome counts.
- Registered model catalogue for the current propulsion and power prototypes, with append-only verification/validation assessment records and derived credibility states.
- Historical mission and spacecraft revision comparison reporting added, removed, and modified requirements/components plus allocations requiring engineering review.
- Transparent component mass totals, user-declared percentage mass margin, and average power generation/load totals using explicit duty-cycle inputs.
- Backend tests covering configuration persistence, revision history, dimensional rejection, duplicate component identifiers and budget arithmetic.
- Frontend controls for mission projects, verification evidence, dataset checksum inspection, propulsion delta-v, power balance and recent model-run retrieval.
- Bounded PDS4 XML label inspection endpoint with namespace-tolerant metadata extraction, PDS4 Product_* root checks, DTD/entity rejection, 5 MiB upload cap, and XML node/depth limits.
- Frontend PDS4 metadata preview and explicit prefill of descriptive manifest fields; authoritative source identity, citations, licence, and science-file checksum remain separately supplied and verified by the user.
- Deterministic orbital regression vectors using the JPL DE440 Earth GM for circular velocity, vis-viva, Keplerian period, escape velocity, and ideal Hohmann transfer.
- Fixed synthetic numerical regression cases for ideal rocket-equation delta-v and constant-average-power energy balance.
- Append-only SPICE kernel metadata registry with typed kernel families, source/release metadata, user-declared SHA-256, optional timezone-aware coverage, time-system, frame, target and terms fields.
- Bounded SPICE kernel artifact upload (1 GiB application limit), server-computed SHA-256 comparison, temporary staging cleanup, and content-addressed local storage.
- Pinned SpiceyPy/CSPICE 8.4.0 inspection subprocess with a 12-second timeout and best-effort POSIX resource limits; validates detected kernel family, extracts SPK object IDs/ET coverage, binary PCK frame IDs, and DSK object IDs. Meta-kernels are not furnished.
- SPICE inspection results are immutable SQLite records; parsing is structural inspection only, not scientific validation.
- PR #14 CI run #419 passed backend lint, all 125 backend tests, frontend TypeScript typecheck, and frontend production build (one existing Starlette/httpx deprecation warning).
- PR #14 artifact-acquisition CI run #369 passed backend lint, all 121 backend tests, frontend TypeScript typecheck, and frontend production build.

## Spacecraft configuration API

- POST /api/v1/missions/projects/{project_id}/spacecraft/configuration — create the initial spacecraft configuration.
- GET /api/v1/missions/projects/{project_id}/spacecraft/configuration — retrieve the latest configuration revision.
- POST /api/v1/missions/projects/{project_id}/spacecraft/configuration/revisions — append a new immutable revision.
- GET /api/v1/missions/projects/{project_id}/spacecraft/budgets — calculate the latest revision's mass and average-power bookkeeping.

Component mass must be represented in kg and power draw/generation in W using the existing EngineeringValue contract. Every value therefore carries provenance, credibility, intended-use and limitations metadata. Component IDs are unique within a revision. Mass margin is a user-entered percentage; no default hardware mass is invented. Power duty cycles are user-entered fractions between zero and one.

The budget endpoint is arithmetic bookkeeping, not a spacecraft simulation or design approval. It does not model battery state of charge, eclipse periods, transient loads, conversion losses, degradation, thermal coupling, harness losses, uncertainty or subsystem interactions. A positive net average power value does not establish power-system adequacy.

## Current model credibility

The available propulsion and power calculators are generic mathematical
prototypes explicitly marked UNVALIDATED. The planetary destination
catalogue marks all mission compatibility as not_assessed. No numerical
planetary environment data or mission feasibility is claimed.

Spacecraft component values inherit their own provenance and credibility fields, but the configuration service does not independently authenticate vendor data or assess component suitability. User-supplied values are not verified merely because they pass schema validation.

## Not implemented

- Historical traceability matrix comparison across mission/configuration revisions and formal verification closure. A first revision change-impact comparison endpoint is now available, but historical allocation snapshots and automated evidence invalidation remain unimplemented.
- Mission lifecycle state transitions, controlled approvals and independent verification/validation acceptance.
- NASA/PDS product download, authoritative PDS4 schema validation, science-data decoding, and coordinate/time transformations.
- Curated body-specific ephemerides, gravity, atmosphere, radiation, terrain and thermal datasets.
- Interplanetary trajectory propagation, launch/arrival windows, high-fidelity orbit insertion and transfer design. The current Hohmann calculator is an ideal circular/coplanar two-body estimate only.
- Destination-specific entry, descent and landing, surface mobility or sample-return models.
- Battery state-of-charge, thermal network, communications link budget and integrated mission simulation.
- Independent verification/validation, uncertainty quantification, sensitivity studies and formal acceptance evidence. The new model governance service records assessment entries but does not perform the independent reviews itself.
- Authentication/authorization, signed/tamper-evident audit records and production deployment hardening.

## Requirement verification evidence status

Verification evidence records are append-only and reference a requirement in the latest project revision. The API checks that the recorded method matches the requirement's declared verification method (unless it is still TBD). Outcomes are evidence entries only: a `pass` does not constitute independent acceptance, formal verification closure, safety approval or flight qualification. Evidence references are user-supplied strings and are not fetched or authenticated.

## Mission project and persistence boundaries

Mission projects preserve user-authored objectives and structured requirements as immutable revisions. Spacecraft configuration records are linked to a mission project and preserve each submitted component set as an immutable revision. These services do not establish technical feasibility, subsystem compliance, or flight readiness. SQLite is intended for local development and early testing; production multi-user deployment requires authenticated access, authorization policies, migrations, backup/recovery and concurrency testing.

## Destination scope

Initial scope: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus and Neptune.
Natural satellites (including the Moon), dwarf planets, comets and asteroids are
future catalogue extensions. Mission-archetype compatibility is not inferred.

## Release boundary

The application is not flight-qualified, not a certified design tool, and not
approved for operational mission decisions. A model may only be promoted beyond
UNVALIDATED when its verification, validation, uncertainty, applicability and
acceptance evidence are reviewed and recorded.

## Requirement-to-subsystem traceability API

- POST /api/v1/missions/projects/{project_id}/traceability/allocations — append an allocation after checking that the requirement exists in the latest mission revision and the component exists in the latest spacecraft configuration.
- GET /api/v1/missions/projects/{project_id}/traceability/matrix — return all requirements in the latest mission revision, their component allocations, unallocated counts, stale component references, and verification evidence outcome counts.

Allocations are append-only. A component removed from a later spacecraft configuration is flagged as stale rather than silently deleted from the traceability record. The matrix counts evidence records but does not interpret a pass as requirement compliance, independent acceptance, or formal verification closure. It currently compares only the latest mission and spacecraft revisions; historical revision comparison is not implemented.

## Model verification and validation governance API

- GET /api/v1/models/governance/catalog — return registered model IDs, versions, equation IDs, assessment counts, latest verification/validation outcomes and derived credibility state.
- POST /api/v1/models/governance/assessments — append a verification or validation assessment for a registered model version and equation.
- GET /api/v1/models/governance/assessments — list immutable assessment records, optionally filtered by model ID and version.

The initial registry contains the ideal rocket-equation prototype and constant-power energy-balance prototype. A model is `unvalidated` until a verification pass is recorded; a verification pass advances it to `verified`; verification and validation passes together advance it to `validated`. A later fail or inconclusive outcome for either assessment type changes the derived state to `review_required`. The status is calculated from the latest recorded outcome for each assessment type. It is not an independent audit, certification, flight qualification, or operational approval. Assessment summaries and evidence references are user-entered and not independently authenticated. Validation dataset references, when supplied, must identify a registered dataset manifest.

## Historical revision change-impact API

- GET /api/v1/missions/projects/{project_id}/traceability/change-impact — compare a baseline and target mission revision plus a baseline and target spacecraft configuration revision. All four revision numbers are required query parameters.

The report identifies added, removed and modified mission requirements and spacecraft components. It flags current project-scoped allocations that reference modified or removed requirements/components. This is a review aid, not a technical acceptability decision. Allocation records are not revisioned, historical verification evidence is not automatically invalidated, and impact severity is not inferred. Reviewers must assess each affected allocation and evidence record.

## Dataset ingestion workflow

The frontend now connects bounded file checksum inspection to source dataset manifest registration. A manifest records provider, product ID, release/version, source URL, citation, retrieval time, file identity, media type, data format, file size, SHA-256 checksum, license/terms, access classification, and optional asset/frame/time metadata. Registered manifests can be browsed in the frontend.

The workflow records metadata and file identity only. Uploaded file bytes are not persisted. The service does not download archive products, decode PDS/FITS/SPICE formats, transform coordinate/time systems, verify source authenticity, or assess scientific correctness. Product metadata and citations must be supplied from the authoritative archive/provider by the user.

## Mission engineering review package

- GET /api/v1/missions/projects/{project_id}/review-package — compile the latest mission project, spacecraft configuration (when present), mass/average-power bookkeeping, latest traceability matrix, and append-only requirement verification evidence into one response.

The package derives an evidence completeness state: `incomplete`, `review_required`, or `evidence_compiled`. These are workflow labels only. `evidence_compiled` does not mean design approval, mission feasibility, flight readiness, or safety acceptance. Findings call out missing spacecraft configuration, unallocated requirements, missing evidence, stale allocations, failed evidence, and inconclusive evidence. Registered dataset manifests and model assessment records can now be linked to mission projects and are included as metadata references. Linking does not authenticate the source or prove scientific applicability. The frontend can export the package as JSON for review.

## Project evidence association API

- POST /api/v1/missions/projects/{project_id}/evidence/datasets — associate an existing registered dataset manifest with a mission project and record its purpose.
- GET /api/v1/missions/projects/{project_id}/evidence/datasets — list linked dataset manifests and their project-specific purpose.
- POST /api/v1/missions/projects/{project_id}/evidence/model-assessments — associate an existing model assessment with a mission project and record its rationale.
- GET /api/v1/missions/projects/{project_id}/evidence/model-assessments — list linked model assessment records and their project-specific rationale.

Associations are append-only and do not duplicate or modify the underlying manifest/assessment records. The review package now includes these linked references. Dataset source URLs, provider details, model assessment summaries, and evidence references remain user-entered metadata; linking does not independently authenticate them or validate scientific applicability.

## Two-body orbital mechanics API

- POST /api/v1/models/orbital-mechanics/circular-orbit — circular orbital velocity.
- POST /api/v1/models/orbital-mechanics/vis-viva — bound elliptical-orbit speed.
- POST /api/v1/models/orbital-mechanics/orbital-period — Keplerian period from semi-major axis.
- POST /api/v1/models/orbital-mechanics/escape-velocity — local two-body escape velocity.
- POST /api/v1/models/orbital-mechanics/hohmann-transfer — ideal two-burn Hohmann transfer delta-v and transfer time.

The model requires SI inputs, including gravitational parameter in m^3/s^2 and orbital radii in m. It uses a fixed central-body point-mass parameter and two-body analytical equations. Hohmann estimates assume circular, coplanar orbits and impulsive burns. These calculators do not use ephemerides, propagate trajectories, model perturbations, solve launch windows, include plane changes or finite burns, or produce a mission delta-v budget. Results are UNVALIDATED and are not flight-performance or operational-safety predictions.

## PDS4 label inspection API

- `POST /api/v1/datasets/pds4/inspect` — accepts a small `.xml` or `.lbl` label and returns selected Identification_Area, Observation_Area, File_Area_Observational, and array metadata.
- This is not authoritative PDS4 schema validation; referenced science data are not fetched, source authenticity is not checked, and scientific coordinate/time interpretation is out of scope.


## Software validation snapshot

- PR #11 CI run #288 passed backend lint, 109 backend tests, frontend TypeScript typecheck, and frontend production build.
- PR #12 CI run #295 passed backend lint, 110 backend tests, frontend TypeScript typecheck, and frontend production build.
- PR #13 CI run #302 passed backend lint, all 110 backend tests, frontend TypeScript typecheck, and frontend production build, including the fixed propulsion and power regression assertions.
- PR #14 CI run #459 passed backend lint, all 129 backend tests, frontend TypeScript typecheck, and frontend production build. One Starlette/httpx TestClient deprecation warning remains.
- PRs #1–#10 also have successful recorded CI runs on their current head commits.
- These checks validate the recorded software build and regression suite only. They do not constitute independent scientific model validation, uncertainty characterization, mission applicability review, formal verification closure, or flight/safety approval.
- The orbital regression vectors use the JPL DE440 Earth GM documented in [ORBITAL_REFERENCE_BENCHMARKS.md](ORBITAL_REFERENCE_BENCHMARKS.md); the orbital model itself remains UNVALIDATED.


## SPICE kernel provenance registry

- `POST /api/v1/ephemeris/spice/kernels` — append a user-declared kernel metadata record.
- `GET /api/v1/ephemeris/spice/kernels` — list records with limit/offset pagination.
- `GET /api/v1/ephemeris/spice/kernels/{kernel_id}` — retrieve one immutable record.

The registration contract supports SPK, PCK, LSK, FK, IK, SCLK, DSK, and meta-kernel (MK) classifications. It records source URL, provider, release, user-declared SHA-256, optional timezone-aware coverage bounds, time system, reference frames, target names, and licence/terms. Duplicate IDs are rejected; registrations are append-only. The registry does not download or store kernel binaries, compute the checksum, authenticate source/terms, inspect kernel contents, or validate coverage/frame declarations. Every record is explicitly marked `user_declared_unverified`.

Registration remains user-declared metadata and does not authenticate source/terms. Artifact acquisition accepts explicit uploads and computes the digest, but only compares it with the user-declared value. Inspection uses pinned SpiceyPy/CSPICE 8.4.0 in a time-limited subprocess and extracts selected metadata; this is not a complete OS sandbox or scientific validation. A test-only frozen NAIF `naif0012.tls` fixture checks the J2000 TDB/UTC reference epoch. The bounded UTC-to-ET API requires an acquired and inspected KPL/LSK, re-hashes the artifact, loads only that LSK in a separate worker, and persists immutable results with the exact artifact digest and toolkit version. It does not evaluate ephemerides or transform frames. The fixture's leap-second table ends at 2017-01-01 and must not be treated as a current operational LSK.


## SPICE artifact acquisition

- `POST /api/v1/ephemeris/spice/kernels/{kernel_id}/artifact` accepts an explicit multipart upload, computes SHA-256 in 1 MiB chunks, rejects mismatches, and stores matching bytes under a content-addressed key.
- `GET /api/v1/ephemeris/spice/kernels/{kernel_id}/artifact` returns acquisition metadata only.
- The source URL is never fetched. The digest match is against a user-declared value and does not independently authenticate publisher or checksum provenance.
- Uploads are capped at 1 GiB in the application. A deployment must also configure upstream request-body limits and protect the storage volume.
- Pinned CSPICE inspection and single-LSK UTC-to-ET conversion are implemented. The conversion worker does not load meta-kernels or arbitrary kernel sets. Frame transformations, ephemeris evaluation, trajectory propagation, uncertainty analysis, and scientific validation are not implemented. The worker is not a complete OS sandbox. Authentication and per-user/team authorization are still absent.
