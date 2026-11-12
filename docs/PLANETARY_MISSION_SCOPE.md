# ORBITOPS Multi-Planetary Mission Scope

**Product direction approved by project owner:** support mission analysis across all
eight planets of the Solar System, rather than designing around one lunar lander.

## Destination scope

The first destination taxonomy includes Mercury, Venus, Earth, Mars, Jupiter,
Saturn, Uranus and Neptune. Planetary classes are descriptive categories only;
no numerical environment constants or engineering suitability are inferred.

Natural satellites (including Earth's Moon), dwarf planets, comets and asteroids
are future destination-catalogue extensions, not silently included in the
initial eight-planet scope.

## Mission archetypes

The platform's mission taxonomy includes:
- Flyby
- Orbiter
- Atmospheric probe
- Entry, descent and landing
- Stationary lander
- Rover
- Sample return

The catalogue lists archetypes as concepts only. It does not claim every mission
type is physically feasible at every planet. A surface rover needs a solid
surface and appropriate environmental and mobility design; gas and ice giants
do not provide a conventional solid surface for a rover or lander. Destination-
specific feasibility must be separately assessed and evidenced.

## Architecture implications

ORBITOPS must be built as a multi-body, multi-mission framework with separable
layers:

1. Mission definition: destination, mission archetype, objectives, payload,
   mission phases, duration and constraints.
2. Scientific data: versioned body/atmosphere/gravity/terrain/radiation/
   ephemeris products, with source, product version, coordinate frame, time
   system, units, coverage, checksum and licence.
3. Environment models: body-specific gravity fields, atmosphere (where
   applicable), thermal environment, radiation and surface/terrain conditions.
4. Vehicle and subsystem models: propulsion, power, thermal control,
   communications, avionics, structures and payload.
5. Mission dynamics: interplanetary trajectory, launch/arrival, orbit
   insertion, entry/descent/landing, surface mobility or sample-return phases
   according to mission archetype.
6. Simulation and evidence: integrated timelines, uncertainty propagation,
   sensitivity analysis, verification cases and validation evidence.

Planet-specific values and model selections must be sourced and versioned.
There must be no universal gravity, atmosphere, temperature, landing or
communications assumptions applied across all destinations.

## Current implementation boundary

The /api/v1/missions/catalog endpoint exposes the eight-planet destination
taxonomy and seven mission archetypes. Every destination is marked
not_assessed for mission feasibility. The endpoint is a planning taxonomy,
not a mission design or physical feasibility engine.

Existing ideal rocket-equation and constant-power models remain generic
mathematical prototypes marked UNVALIDATED. They are not yet connected to
planetary ephemerides, body environments, vehicle configurations or mission
profiles.

## Engineering release boundary

ORBITOPS is an engineering exploration foundation. It is not flight-qualified,
not a certified design tool and not approved for operational decisions.
A planetary model may only be promoted beyond UNVALIDATED after its intended
use, source data, verification, validation, uncertainty, applicability and
acceptance evidence are reviewed.
