"""Simple constant-power energy balance model with explicit limitations."""
from datetime import datetime
from math import isfinite
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engineering.provenance import CredibilityStatus, EngineeringValue, ProvenanceClass
from app.engineering.units import Dimension

MODEL_ID = "power.simple-energy-balance"
MODEL_VERSION = "0.1.0"
EQUATION_ID = "POWER.SIMPLE_ENERGY_BALANCE.V1"


class SimpleEnergyBalanceRequest(BaseModel):
    """Aggregated average power and duration inputs, each with provenance."""

    model_config = ConfigDict(extra="forbid")

    supply_power: EngineeringValue
    load_power: EngineeringValue
    duration: EngineeringValue
    intended_use: Annotated[str, Field(min_length=1, max_length=500)]

    @model_validator(mode="after")
    def inputs_must_have_expected_units(self) -> "SimpleEnergyBalanceRequest":
        expected = (
            (self.supply_power, "W", Dimension.POWER, "supply_power", True),
            (self.load_power, "W", Dimension.POWER, "load_power", False),
            (self.duration, "h", Dimension.TIME, "duration", False),
        )
        for value, unit, dimension, name, allow_zero in expected:
            if value.unit != unit or value.dimension != dimension:
                raise ValueError(f"{name} must use {unit} with dimension {dimension.value}")
            if value.value < 0 if allow_zero else value.value <= 0:
                raise ValueError(f"{name} is outside its permitted range")

        value_ids = {
            self.supply_power.value_id,
            self.load_power.value_id,
            self.duration.value_id,
        }
        if len(value_ids) != 3:
            raise ValueError("Each input must have a unique value_id")
        return self


class SimpleEnergyBalanceResult(BaseModel):
    supply_energy: EngineeringValue
    load_energy: EngineeringValue
    energy_margin: EngineeringValue
    margin_fraction: EngineeringValue
    input_values: list[EngineeringValue]
    equation_id: str
    model_version: str
    assumptions: list[str]
    limitations: list[str]
    run_id: str | None = None
    created_at: datetime | None = None
    model_id: str = MODEL_ID


def calculate_simple_energy_balance(
    request: SimpleEnergyBalanceRequest,
) -> SimpleEnergyBalanceResult:
    """Compare constant supply and load over one fixed interval."""
    duration_h = request.duration.value
    supply_energy = request.supply_power.value * duration_h
    load_energy = request.load_power.value * duration_h
    energy_margin = supply_energy - load_energy
    margin_fraction = energy_margin / load_energy

    if not all(isfinite(value) for value in (supply_energy, load_energy, energy_margin, margin_fraction)):
        raise ValueError("Model output is outside the supported finite numeric range")

    assumptions = [
        "Supply power and load power remain constant for the full entered duration.",
        "Both powers are measured at the same declared system boundary.",
        "Energy is calculated as average power multiplied by elapsed time.",
        "No storage or conversion behavior is inferred from the net energy margin.",
    ]
    limitations = [
        "Excludes battery capacity, state of charge, charge/discharge efficiency and depth of discharge.",
        "Excludes eclipse schedules, solar incidence, array degradation and thermal derating.",
        "Excludes transient loads, power electronics losses, wiring losses and fault cases.",
        "A positive energy margin does not prove instantaneous power sufficiency or mission survival.",
        "This implementation is unvalidated and must not be used for flight or operational decisions.",
    ]

    def calculated_value(
        value_id: str,
        name: str,
        value: float,
        unit: str,
        dimension: Dimension,
    ) -> EngineeringValue:
        return EngineeringValue(
            value_id=value_id,
            name=name,
            value=value,
            unit=unit,
            dimension=dimension,
            provenance=ProvenanceClass.CALCULATED,
            equation_id=EQUATION_ID,
            model_version=MODEL_VERSION,
            credibility=CredibilityStatus.UNVALIDATED,
            intended_use=request.intended_use,
            limitations=limitations,
        )

    return SimpleEnergyBalanceResult(
        supply_energy=calculated_value(
            "calculated.supply-energy",
            "Available supply energy",
            supply_energy,
            "Wh",
            Dimension.ENERGY,
        ),
        load_energy=calculated_value(
            "calculated.load-energy",
            "Load energy demand",
            load_energy,
            "Wh",
            Dimension.ENERGY,
        ),
        energy_margin=calculated_value(
            "calculated.energy-margin",
            "Net energy margin",
            energy_margin,
            "Wh",
            Dimension.ENERGY,
        ),
        margin_fraction=calculated_value(
            "calculated.margin-fraction",
            "Energy margin fraction",
            margin_fraction,
            "1",
            Dimension.DIMENSIONLESS,
        ),
        input_values=[request.supply_power, request.load_power, request.duration],
        equation_id=EQUATION_ID,
        model_version=MODEL_VERSION,
        assumptions=assumptions,
        limitations=limitations,
    )
