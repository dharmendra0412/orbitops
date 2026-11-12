# ORBITOPS Engineering Status

**Snapshot date:** 2026-11-12  
**Branch:** engineering-grade-foundation  
**Status:** Engineering foundation implemented; mission-specific engineering analysis is not complete.

## Implemented and CI-verified

- FastAPI + React/TypeScript/Vite application foundation.
- Engineering value contracts with units, dimensional checks, provenance classes,
  credibility status, equation/model references, intended use and limitations.
- Dataset manifest validation and immutable SQLite metadata registry.
- SHA-256 file inspection with a 100 MiB limit; uploaded file bytes are not persisted.
- Candidate NASA/PDS lunar data-source review; no dataset or landing site approved.
- SQLite model-run snapshots preserving inputs, outputs, model/equation IDs,
  assumptions, limitations and UTC run time.
- Ideal Tsiolkovsky rocket-equation delta-v prototype.
- Constant-average-power energy-balance prototype.
- Frontend controls for dataset checksum inspection, propulsion delta-v, power
  balance and recent model-run retrieval.

The latest verified CI run completed backend Ruff checks, 44 backend tests, and
frontend TypeScript/production build successfully. See the GitHub Actions workflow
history on the feature branch for individual runs.

## Current model credibility

Both available engineering calculators are explicitly marked **UNVALIDATED**.
They are generic mathematical prototypes and do not represent a selected lander,
engine, power architecture, lunar site, or mission profile.

## Not implemented

- NASA/PDS product download, label parsing, decoding, checksum verification against
  remote archive metadata, and coordinate/time transformations.
- A selected lunar site, mission profile, mission requirements, or approved
  environmental dataset.
- Trajectory propagation, lunar descent/landing dynamics, guidance/navigation/control,
  engine performance maps, throttling, plume effects or landing stability.
- Battery state-of-charge, eclipse-aware power scheduling, solar-array sizing,
  thermal network/radiative balance, communications link budget, fault analysis,
  or integrated mission simulation.
- Independent model verification/validation against accepted reference cases,
  uncertainty quantification, sensitivity studies, and formal acceptance evidence.
- Authentication/authorization, signed/tamper-evident audit records, distributed
  storage, deployment hardening, and production observability.

## Required decisions before mission-specific modelling

The following must be supplied or formally approved rather than invented:
1. Mission profile and operational concept.
2. Payload and mission duration requirements.
3. Candidate lunar region/site and required coordinate reference frame.
4. Power architecture and operating modes.
5. Propulsion/landing architecture and applicable hardware performance data.
6. Applicable constraints, safety margins, and acceptance criteria.

## Release boundary

The application is a development and engineering exploration foundation. It is not
flight-qualified, not a certified design tool, and not approved for operational
mission decisions. A model may only be promoted beyond UNVALIDATED when its
verification, validation, uncertainty, applicability, and acceptance evidence
are reviewed and recorded.
