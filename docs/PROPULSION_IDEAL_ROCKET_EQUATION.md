# Ideal Rocket-Equation Propulsion Model

**Model ID:** PROPULSION.IDEAL_ROCKET_EQUATION.V1  
**Implementation version:** 0.1.0  
**Credibility:** UNVALIDATED  
**Intended use:** Transparent idealized delta-v calculation for engineering exploration.

## Governing equation

NASA Glenn's ideal rocket equation gives:

`delta_v = Isp * g0 * ln(m_initial / m_final)`

ORBITOPS uses entered dry mass as final mass and dry mass plus propellant mass
as initial mass. Specific impulse is entered in seconds. The standard acceleration
of gravity is `g0 = 9.80665 m/s^2`, used as the conventional conversion factor in
the definition of specific impulse. It is not lunar surface gravity.

## Inputs and traceability

The API requires three EngineeringValue records: dry mass (kg), propellant mass
(kg), and specific impulse (s). Each input must carry its own ID, provenance,
assumption/source metadata, intended use, and credibility status. The model
returns calculated EngineeringValue records with equation IDs, model version,
input references, and UNVALIDATED credibility.

## Assumptions and exclusions

The model assumes constant effective exhaust velocity and complete consumption
of the entered propellant. It uses the ideal free-space equation and excludes
external forces. It does not include lunar gravity losses, trajectory geometry,
finite-burn steering, engine transients, pressure mismatch, residual propellant,
landing guidance, navigation, control, or structural constraints.

Therefore, this result is an ideal delta-v capability estimate—not a lunar landing
mission budget, flight-performance prediction, or safety assessment. It must not
be used for flight or operational decisions.

## API

POST /api/v1/models/propulsion/ideal-delta-v

Sources:
- [NASA Glenn — Ideal Rocket Equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/)
- [NIST — CODATA standard acceleration of gravity](https://physics.nist.gov/cgi-bin/cuu/Value?gn)
