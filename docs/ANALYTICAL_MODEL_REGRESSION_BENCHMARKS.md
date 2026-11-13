# Analytical model regression benchmarks

**Purpose:** Preserve fixed numerical checks for the ideal rocket-equation and constant-average-power bookkeeping implementations.

These tests are software regression evidence. They do not certify a propulsion system, power system, mission profile, or model applicability.

## Ideal rocket equation

The test vector uses synthetic values:

- Dry mass: `1,000 kg`
- Propellant mass: `1,000 kg`
- Specific impulse: `300 s`
- Standard gravity: `9.80665 m/s^2`

The implementation uses the ideal Tsiolkovsky equation:

`delta_v = Isp * g0 * ln(m_initial / m_final)`

Expected outputs:

- Initial mass: `2,000 kg`
- Initial/final mass ratio: `2`
- Ideal delta-v: `2,039.2355394714561 m/s`

Reference material:
- [NASA Glenn — Ideal Rocket Equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/)
- [NIST — Standard acceleration of gravity](https://physics.nist.gov/cgi-bin/cuu/Value?gn)

Standard gravity is the conventional conversion factor for specific impulse. It is not a planetary surface-gravity input.

## Constant-average-power energy balance

The deterministic synthetic test case uses:

- Average supply power: `150 W`
- Average load power: `100 W`
- Duration: `10 h`

Expected outputs:

- Supply energy: `1,500 Wh`
- Load energy: `1,000 Wh`
- Net energy margin: `500 Wh`
- Margin fraction relative to load energy: `0.5`

A deficit case also checks a `-500 Wh` net margin and a `-0.5` margin fraction.

## Validation boundary

These tests check deterministic arithmetic, expected units, and stable output values for the stated inputs. They do not validate input provenance, engine performance, battery behavior, thermal effects, power transients, uncertainty, subsystem interactions, mission requirements, or operational suitability.

Both model implementations remain `UNVALIDATED`. Independent engineering review and applicable test/flight evidence are required before promoting their credibility state or using them for mission decisions.
