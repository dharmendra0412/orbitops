# ORBITOPS — Spacecraft Component Catalog Specification

## Catalog principles

Every component is a versioned data record, not a hard-coded UI card. A component may contain applicable engineering properties; non-applicable properties are omitted or explicitly null with reason, never silently treated as zero. Each value carries units, value class, provenance and uncertainty/quality notes. No NASA hardware specification is invented. MVP's starter catalog should use clearly labeled fictional/illustrative game components unless a sourced public specification is deliberately curated and reviewed.

## Data model

```json
{
  "component_id": "solar_fixed_80",
  "catalog_version": "lander-mvp-1",
  "name": "Polar Array (game example)",
  "category": "power_generation",
  "description": "Illustrative module for teaching illumination trade-offs.",
  "properties": {
    "mass_kg": {"value": 18.0, "unit": "kg", "value_class": "illustrative", "provenance_ref": null, "notes": "game parameter"},
    "power_generation_rated_w": {"value": 80.0, "unit": "W", "value_class": "illustrative", "provenance_ref": null, "notes": "rated output before illumination/efficiency/health scaling"},
    "cost_credits": {"value": 14, "unit": "credit", "value_class": "illustrative", "provenance_ref": null, "notes": "game currency"},
    "event_model_ref": {"value": "ARRAY_OUTPUT_DEGRADE", "unit": "event_rule_id", "value_class": "illustrative", "provenance_ref": null, "notes": "seeded game hazard, not real reliability"}
  },
  "interfaces": ["power_bus"],
  "quantity_limits": {"min": 0, "max": 2},
  "compatibility": {"requires": [], "excludes": []},
  "provenance": [{"property_path": "properties.mass_kg", "kind": "illustrative", "citation": null}],
  "effective_from": "lander-mvp-1",
  "schema_version": "1"
}
```

## Common property groups

- Identity: stable ID, display name, category, description, catalog/schema versions.
- Physical: mass kg, dimensions if used, mounting/slot interface.
- Electrical: nominal/peak W, voltage if modeled, duty-cycle bounds, energy/capacity, charge/discharge efficiency.
- Mission: instrument capability/objective tags, decimal MB/s or MB/h data rate, decimal MB storage, operation constraints.
- Propulsion: propellant mass kg, specific impulse seconds, thrust N if modeled, allowable burns. Only provide data with documented source or illustrative label.
- Communications: downlink rate, band, link model complexity flag, antenna interface. MVP rate is game parameter unless an audited link budget is adopted.
- Economics: cost credits and scenario-specific availability.
- Reliability: explicit model and parameter class; do not call game event chance a real reliability rating.
- Validation: allowable ranges, required/excluded interfaces and compatibility rules.

## Value provenance taxonomy

`sourced`: value transcribed from a cited primary document with page/table/version and applicable context. `calculated`: derived by a cited formula from identified sourced/illustrative inputs; retain formula ID and input links. `illustrative`: invented for gameplay and labeled in catalog/UI/report. Every catalog numeric property must be one of these; derived values should be produced at run time rather than editorially entered where feasible.

## Compatibility and resolution

Design stores component ID, slot and quantity. Backend resolves it against the pinned catalog version and checks slot compatibility, required dependencies, quantity limits, duplicates, ranges and budget. Component updates create a new catalog version; past revisions/runs remain pinned. Catalog publication validates units, provenance completeness, unique IDs and schema. Use small, coherent choices rather than implying a complete flight-qualified bill of materials.

Every applicable numeric field is stored in the normalized property name and unit specified above; each property carries `value_class` (`sourced`, `calculated`, or `illustrative`), `provenance_ref` (required for sourced/calculated, null only for illustrative), and notes. The following quantity limits and validation rules are authoritative for `lander-mvp-1`; quantities are integers and cost/mass multiply by quantity. Exactly one launcher (`launcher_light` XOR `launcher_heavy`), one bus (`lander_bus_basic` XOR `lander_bus_reinforced`), and one `descent_engine_demo` are required. Select 1–2 solar arrays (`solar_fixed_80` or `solar_mast_140`, combined quantity ≤2); 1–2 batteries (`battery_600` or `battery_1200`, combined quantity ≤2); one or more science instruments, with each of the three instrument IDs quantity 0–1; exactly one radio (`x_band_radio_demo` XOR `low_rate_radio_demo`); exactly one recorder (`data_store_256` XOR `data_store_1024`); exactly one thermal package (`thermal_survival_basic` XOR `thermal_survival_insulated`). No duplicate component ID/slot pair; quantity outside these bounds is invalid. These are game configuration rules, not hardware constraints.

Interface contract: either bus is the root and supplies `lander_mount`, `power_bus`, `instrument_bus`, `data_bus`, `antenna_mount`, `thermal_mount`, `propulsion_interface` and `mast_mount`; reinforced bus additionally supplies `landing_gear_interface`. Solar arrays require `power_bus`; the mast array also requires `mast_mount`. Batteries require `power_bus`; descent package requires `propulsion_interface` and `power_bus`; instruments require `instrument_bus` and `data_bus`; radios require `antenna_mount`, `data_bus` and `power_bus`; recorders require `data_bus` and `power_bus`; thermal packages require `thermal_mount` and `power_bus`. Launcher has no landed component interface and only applies payload cap before separation. No separate mount/harness component is implied.

## Initial MVP categories

Structure/bus; solar generation; battery/storage; propulsion; science instrument; data storage; communications; thermal/power operations as a simplified subsystem. Target a compact selection of alternatives for each, enough to create meaningful trade-offs. Values are game balance settings until sourced evidence is reviewed. Keep catalog data in seed JSON/DB migration, not frontend constants.

## Concrete proposed catalog: `lander-mvp-1`

Every number below is an **illustrative game parameter**, not a NASA hardware specification. Power is steady draw or rated generation as labeled; cost is abstract credits. Every installed spacecraft component except the launcher and bus requires one bus. `launcher_*` is a mission choice and not landed mass. Exactly one bus, launcher and descent package are required. Required interfaces and dependencies are validation rules.

| ID / category | Mass kg | Power W | Cost cr | Compatibility / dependency | Provenance |
|---|---:|---:|---:|---|---|
| `launcher_light` Launcher | 0 landed; 900 kg payload cap | 0 | 18 | Select one; cap includes pre-separation spacecraft + propellant | Illustrative scenario value |
| `launcher_heavy` Launcher | 0 landed; 1,800 kg payload cap | 0 | 32 | Select one; same payload rule | Illustrative scenario value |
| `lander_bus_basic` Structure | 120 | 8 | 16 | Exactly one; mounts all; required interfaces | Illustrative |
| `lander_bus_reinforced` Structure | 190 | 12 | 25 | Exactly one; landing gear interface | Illustrative |
| `solar_fixed_80` Power | 18 | 0 draw; 80 generation W | 14 | One or more on bus; output scaled by illumination | Illustrative |
| `solar_mast_140` Power | 32 | 0 draw; 140 generation W | 23 | Bus mast mount; output scaled by illumination | Illustrative |
| `battery_600` Energy storage | 22 | 0; 600 Wh | 12 | Power bus | Illustrative |
| `battery_1200` Energy storage | 41 | 0; 1,200 Wh | 21 | Power bus | Illustrative |
| `descent_engine_demo` Propulsion | 95 | 35 during descent | 24 | Exactly one; illustrative 360 kg propellant load | Illustrative |
| `neutron_spectrometer_demo` Science | 16 | 28 active | 16 | Instrument bus; 0.8 MB/h while active | Illustrative |
| `near_ir_spectrometer_demo` Science | 12 | 22 active | 14 | Instrument bus; 1.2 MB/h while active | Illustrative |
| `panoramic_camera_demo` Science | 7 | 12 active | 9 | Instrument bus; 2 MB per observation | Illustrative |
| `x_band_radio_demo` Communication | 14 | 24 during contact | 15 | Antenna mount/contact; 1.5 MB/min game rate (.025 MB/s) | Illustrative |
| `low_rate_radio_demo` Communication | 8 | 10 during contact | 9 | Antenna mount/contact; 0.3 MB/min game rate (.005 MB/s) | Illustrative |
| `data_store_256` Storage | 5 | 3 | 6 | Data bus; 256 MB capacity | Illustrative |
| `data_store_1024` Storage | 11 | 6 | 12 | Data bus; 1,024 MB capacity | Illustrative |
| `thermal_survival_basic` Thermal | 15 | 45 when scheduled | 10 | Power + battery; survival priority | Illustrative |
| `thermal_survival_insulated` Thermal | 21 | 18 when scheduled | 15 | Bus; illustrative 0.65 load multiplier | Illustrative |

Transfer requirement 700 m/s, descent requirement 1,300 m/s, descent Isp 300 s, 360 kg propellant, solar efficiency 0.85, charge/discharge efficiency 0.95, battery initial state 80%, and all component parameters are illustrative. Do not call these NASA hardware specifications. Catalog schema must carry `value_class`, unit, source reference and notes per property. Absent properties are null/not applicable, never silently zero. Require bus, launcher, descent, power generation, battery, comms, storage, thermal package and ≥1 science instrument. Feasible designs are distinguished from structurally valid designs so players may simulate failure consequences.

## Canonical catalog normalization and consistency report

This addendum supersedes negative generation notation and previous inconsistent scenario defaults. Set transfer requirement **700 m/s**, descent **1,300 m/s**, descent Isp **300 s**, loaded propellant default **360 kg**, procurement cap **140 credits**, solar efficiency `.85`, battery initial state `.80C`, and charge/discharge efficiencies `.95`, all illustrative game parameters. Catalog values are not NASA hardware specifications.

Canonical property schema separates `mass_kg`, `power_draw_w`, `power_generation_rated_w`, `battery_capacity_wh`, `storage_capacity_mb`, `data_generation_rate_mb_per_h`, `downlink_rate_mb_per_s`, `cost_credits`, `compatibility`, `dependencies`, and per-property `{value_class, provenance_ref, unit, notes}`. Generation is nonnegative rated power (solar A=80 W; B=140 W); draw is a separate nonnegative field. Data rates are explicit: neutron `.8 MB/h`, near-IR `1.2 MB/h`, radio high `1.5 MB/min = .025 MB/s`, radio low `.3 MB/min = .005 MB/s`; camera is `2 MB/observation`. Storage remains decimal MB. Battery capacity is not generation. Launcher payload cap is a separate property, not mass. Null means not applicable; omitted required numeric fields fail catalog validation and are never coerced to zero.

**18-item compatibility review:** all IDs below remain in `lander-mvp-1`; each row must provide every applicable normalized property and provenance object. Launcher light/heavy: mutually exclusive, payload cap 900/1,800 kg, no spacecraft interfaces, source class illustrative. Basic/reinforced bus: exactly one, required lander/power/instrument/data interfaces, illustrative. Solar fixed/mast: compatible bus power interface, rated generation 80/140 W; mast mount needed for mast; illustrative. Battery 600/1200: power interface, 600/1200 Wh; illustrative. Descent demo: exactly one, propulsion interface; 35 W draw during descent; 300 s illustrative Isp; propellant amount is mission-level 360 kg input, not component mass; illustrative. Neutron, near-IR and camera: instrument bus; respective draw 28/22/12 W; data rates `.8 MB/h`, `1.2 MB/h`, and `2 MB/observation`; illustrative. X/low-rate radio: antenna + data bus + contact schedule; draw 24/10 W during contact; `.025/.005 MB/s`; illustrative. Recorder 256/1024: data bus, draw 3/6 W, capacity 256/1,024 MB; illustrative. Thermal basic/insulated: bus/power interface; draw 45/18 W when scheduled; insulated multiplier `.65` only on thermal load; illustrative. Existing masses/costs in the table remain illustrative. All 18 satisfy schema once mapped to these separated properties; no row may encode generation as negative load.

**Per-item property semantics and provenance:** every value in the 18-row table above is `illustrative`; its property-level `provenance_ref` is null and notes identify it as a game parameter. Units are `kg` for landed component mass, `kg` for launcher payload cap (a separate constraint and not component mass), `W` for steady/rated/during-operation power, `Wh` for battery capacity, `MB` decimal for storage, `MB/h` for continuous instrument data, `MB/observation` for camera data, `MB/s` for radio throughput, `s` for Isp, and `credit` for cost. For every row, the table's mass and cost apply per unit. Launcher discarded mass is zero landed mass. Solar generation is nonnegative rated W and is scaled by environment illumination × `.85` efficiency × health. Battery capacity is stored energy, not generation; battery operating efficiencies and initial state are scenario/ruleset inputs. The descent package's 300 s Isp and 35 W descent draw are package-level illustrative parameters; the 360 kg propellant is mission-level and counted once, not as component mass. Instrument/radio rates are applied only to actual powered seconds. Camera generates exactly once per fully completed observation. Recorder capacity is decimal MB. Thermal insulated `.65` is a multiplier on the scheduled heater demand, not a power-generation or efficiency term. No per-component reliability percentage is claimed: illustrative stochastic hazards belong to pinned event ruleset `event-v1`, and must be labeled game-event probabilities rather than component reliability.

Reliability field for each item is `event_model_ref` with `value_class=illustrative`, pointing to its applicable seeded rule or null with reason: solar arrays → `ARRAY_OUTPUT_DEGRADE`; science instruments → `INSTRUMENT_SAFE_MODE`; radios → `RADIO_CONTACT_SKIP`; thermal packages → `THERMAL_LOAD_SPIKE`; launcher → `null` (pre-mission selection has no stochastic rule); bus, batteries, descent package and storage → `null` (no stochastic rule in MVP). Null means no modeled random event, never a 100% reliability claim. Rule probabilities/impacts remain in the pinned event ruleset and all are explicitly illustrative. The electrical heater request is derived from pinned environment schedule values `heater_requested_w` and `heater_survival_min_w`, scaled by the selected thermal package's `heater_load_multiplier` (basic `1.0`, insulated `.65`); `heater_power_limit_w` is the maximum supported draw (basic 45 W, insulated 18 W). The environment must satisfy `0≤heater_survival_min_w≤heater_requested_w`; a design whose scaled request exceeds its package limit fails the `SURVIVAL_HEATER_CAPACITY` feasibility gate. These are game-rule parameters; no temperature state or physical thermal analysis is implied.

Illustrative scenario objective tags used by the scoring rules: `neutron_spectrometer_demo → volatile_proxy_context`; `near_ir_spectrometer_demo → surface_spectral_context`; `panoramic_camera_demo → site_context_imaging`. These are educational capability tags, not claims about detection performance. Scenario owns the required-objective set and each scheduled observation's stable ID, matching instrument, interval and expected payload. A valid observation requires the full powered interval, surviving instrument, and storage of its complete expected payload (camera 2 MB atomic; continuous instrument rate × actual active seconds). Generated but overflowed bytes are not valid observation evidence. Downlinked science data is counted separately from acquired/stored observations.

The procurement cap remains **140 credits**. The corrected minimum required combination costs 118 credits; the prior 123-credit statement was an arithmetic error. Propellant is a mission-level mass input and is counted once in launcher payload check; it is not duplicated in component mass. Required categories remain bus, launcher, descent, generation, battery, science, communication, storage and thermal survival.

Scenario procurement budget is 140 credits (illustrative). Sum launcher cost and each selected component cost; quantity multiplies cost. The launcher payload limit applies to bus, mounted components and propellant before separation; launcher mass is excluded. The listed launcher “mass” is zero landed mass because it is discarded, with payload cap stored as a separate field.

**Minimum-cost correction:** the cheapest required combination is light launcher 18 + basic bus 16 + fixed solar 14 + 600 Wh battery 12 + descent package 24 + panoramic camera 9 + low-rate radio 9 + 256 MB recorder 6 + basic thermal package 10 = **118 credits**. The earlier 123-credit claim was an arithmetic error, not an omitted requirement. The 140-credit budget remains and leaves 22 credits for upgrades. Camera satisfies the catalog's one-instrument minimum and contributes only site-context imaging; it does not claim to detect water.

For that same configuration, landed component dry mass is `120+18+22+95+7+8+5+15=290 kg`; add 360 kg mission-level propellant once for 650 kg launcher payload, below the light launcher's illustrative 900 kg cap. Launcher zero landed mass is excluded. This is a catalog arithmetic check, not a validated launch vehicle performance claim.

