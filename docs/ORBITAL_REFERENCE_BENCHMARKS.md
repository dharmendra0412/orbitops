# Orbital mechanics numerical regression benchmarks

**Purpose:** Freeze reproducible numerical test cases for the two-body analytical implementation.

These cases are software regression checks, not independent model certification, flight-dynamics validation, or evidence that the assumptions apply to a mission.

## Reference gravitational parameter

The Earth gravitational parameter used by the benchmark is the JPL Solar System Dynamics DE440 value:

- `GM_Earth = 398600.435507 km^3/s^2`
- Converted input: `3.98600435507e14 m^3/s^2`

Source: [JPL Solar System Dynamics — Astrodynamic Parameters](https://ssd.jpl.nasa.gov/astro_par.html). The JPL table identifies planetary masses/GM values as derived from DE440.

## Deterministic test geometry

The test cases use the following radii as deliberately selected mathematical inputs, not as recommended or operational orbit definitions:

- Initial circular radius: `7,000,000 m`
- Target circular radius: `42,164,000 m`
- Hohmann transfer semi-major axis: arithmetic mean of those radii.

## Frozen numerical outputs

The expected values below are stored in `backend/tests/test_orbital_mechanics.py` and checked with a relative tolerance of `1e-10`.

| Quantity | Expected value |
|---|---:|
| Circular velocity at 7,000 km | 7,546.053230539979 m/s |
| Vis-viva speed at transfer periapsis | 9,882.84899447982 m/s |
| Circular-orbit period at 7,000 km | 5,828.516683695568 s |
| Two-body escape speed at 7,000 km | 10,671.730821018946 m/s |
| Hohmann first burn | 2,336.795763939841 m/s |
| Hohmann second burn | 1,433.9314395986582 m/s |
| Hohmann total delta-v | 3,770.7272035384995 m/s |
| Hohmann transfer time | 19,178.154357098887 s |

The numerical values are fixed regression vectors computed from the documented two-body equations and the cited GM input. They are intended to catch implementation drift, unit conversion mistakes, and accidental changes to the analytical model.

## What this does not validate

- The correctness, uncertainty, frame realization, or mission applicability of a selected GM value.
- Real ephemerides, launch windows, departure/arrival geometry, or trajectory propagation.
- Perturbations, nonspherical gravity, third-body effects, atmospheric drag, finite burns, plane changes, or navigation errors.
- A complete mission delta-v budget, spacecraft performance, feasibility, or operational safety.

The orbital model credibility remains `UNVALIDATED`. A domain expert must review the equations, reference data, intended use, and applicability before any engineering or mission decision.
