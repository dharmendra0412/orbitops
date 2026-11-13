# ORBITOPS Engineering Status

**Snapshot date:** 2026-11-13  
**Branch:** feature/project-evidence-linking  
**Product scope:** Multi-planetary mission engineering foundation  
**Status:** Mission workspaces, verification evidence capture, and spacecraft configuration/budget services, and requirement-to-component traceability, and model verification/validation evidence governance, and historical revision change-impact analysis, and frontend checksum-to-manifest registration workflow, and consolidated mission review package, and project-scoped dataset/model evidence associations implemented; engineering acceptance remains pending.

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
- NASA/PDS product download, label parsing, decoding, coordinate/time transformations.
- Curated body-specific ephemerides, gravity, atmosphere, radiation, terrain and thermal datasets.
- Interplanetary trajectory propagation, launch/arrival windows, orbit insertion and transfer design.
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
