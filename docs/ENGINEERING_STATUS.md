# ORBITOPS Engineering Status

**Snapshot date:** 2026-11-13  
**Branch:** feature/spacecraft-configuration  
**Product scope:** Multi-planetary mission engineering foundation  
**Status:** Mission workspaces, verification evidence capture, and initial spacecraft configuration/budget services implemented; engineering acceptance remains pending.

## Implemented

- FastAPI + React/TypeScript/Vite application foundation.
- Engineering value contracts with units, dimensional checks, provenance classes,
  credibility status, equation/model references, intended use and limitations.
- Dataset manifest validation and immutable SQLite metadata registry.
- SHA-256 file inspection with a 100 MiB limit; uploaded file bytes are not persisted.
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

- Requirement-to-component traceability links and formal verification closure.
- Mission lifecycle state transitions, controlled approvals and independent verification/validation acceptance.
- NASA/PDS product download, label parsing, decoding, coordinate/time transformations.
- Curated body-specific ephemerides, gravity, atmosphere, radiation, terrain and thermal datasets.
- Interplanetary trajectory propagation, launch/arrival windows, orbit insertion and transfer design.
- Destination-specific entry, descent and landing, surface mobility or sample-return models.
- Battery state-of-charge, thermal network, communications link budget and integrated mission simulation.
- Independent verification/validation, uncertainty quantification, sensitivity studies and formal acceptance evidence.
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
