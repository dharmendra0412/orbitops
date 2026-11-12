# Simple Constant-Power Energy Balance Model

**Model ID:** POWER.SIMPLE_ENERGY_BALANCE.V1  
**Implementation version:** 0.1.0  
**Credibility:** UNVALIDATED

## Governing calculation

For one interval with constant average supply and load power:

- Supply energy (Wh) = supply power (W) × duration (h)
- Load energy (Wh) = load power (W) × duration (h)
- Net energy margin (Wh) = supply energy − load energy
- Margin fraction = net energy margin ÷ load energy

Inputs are EngineeringValue records with explicit units, provenance, intended use,
and credibility. Outputs carry the equation ID, model version, input references,
and UNVALIDATED credibility.

## Assumptions and exclusions

The model assumes constant average powers over the entire interval and that supply
and load are measured at the same system boundary. It does not infer battery
behavior from the net energy margin.

It excludes battery capacity, state of charge, charge/discharge efficiency, depth
of discharge, eclipse schedules, solar incidence, array degradation, thermal
derating, transient loads, conversion/wiring losses, and fault cases. A positive
energy margin does not prove instantaneous power sufficiency or mission survival.

This model is a preliminary bookkeeping calculation only. It is not a spacecraft
power-system design or an operational safety result.

## API

POST /api/v1/models/power/simple-energy-balance
