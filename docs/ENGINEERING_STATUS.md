# ORBITOPS Engineering Status

**Snapshot date:** 2026-11-12  
**Branch:** engineering-grade-foundation  
**Product scope:** Multi-planetary mission engineering foundation  
**Status:** Multi-planetary taxonomy and engineering foundation implemented; planetary mission analysis is not complete.

## Implemented and CI-verified

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
- Frontend controls for dataset checksum inspection, propulsion delta-v, power
  balance and recent model-run retrieval.

## Current model credibility

The available propulsion and power calculators are generic mathematical
prototypes explicitly marked UNVALIDATED. The planetary destination
catalogue marks all mission compatibility as not_assessed. No numerical
planetary environment data or mission feasibility is claimed.

## Not implemented

- Mission profile creation, storage, lifecycle and requirements management.
- NASA/PDS product download, label parsing, decoding, coordinate/time transformations.
- Curated body-specific ephemerides, gravity, atmosphere, radiation, terrain and thermal datasets.
- Interplanetary trajectory propagation, launch/arrival windows, orbit insertion and transfer design.
- Destination-specific entry, descent and landing, surface mobility or sample-return models.
- Battery state-of-charge, thermal network, communications link budget and integrated mission simulation.
- Independent verification/validation, uncertainty quantification, sensitivity studies and formal acceptance evidence.
- Authentication/authorization, signed/tamper-evident audit records and production deployment hardening.

## Destination scope

Initial scope: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus and Neptune.
Natural satellites (including the Moon), dwarf planets, comets and asteroids are
future catalogue extensions. Mission-archetype compatibility is not inferred.

## Release boundary

The application is not flight-qualified, not a certified design tool, and not
approved for operational mission decisions. A model may only be promoted beyond
UNVALIDATED when its verification, validation, uncertainty, applicability and
acceptance evidence are reviewed and recorded.
