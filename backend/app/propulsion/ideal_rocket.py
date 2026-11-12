"""Ideal Tsiolkovsky rocket-equation model with explicit limitations."""
from math import isfinite, log
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engineering.provenance import (
    CredibilityStatus,
    EngineeringValue,
    ProvenanceClass,
    SourceReference,
)
from app.engineering.units import Dimension

MODEL_VERSION = "0.1.0"
DELTA_V_EQUATION_ID = "PROPULSION.IDEAL_ROCKET_EQUATION.V1"
MASS_SUM_EQUATION_ID = "PROPULSION.INITIAL_MASS_SUM.V1"
MASS_RATIO_EQUATION_ID = "PROPULSION.MASS_RATIO.V1"

STANDARD_GRAVITY = EngineeringValue(
    value_id="constant.standard_gravity",
    name="Standard acceleration of gravity",
    value=9.80665,
    unit="m/s^2",
    dimension=Dimension.ACCELERATION,
    provenance=ProvenanceClass.SOURCED,
    source=SourceReference(
        source_id="NIST-CODATA-gn",
        title="Standard acceleration of gravity",
        url="https://physics.nist.gov/cgi-bin/cuu/Value?gn",
        version_or_release="NIST CODATA reference value",
    ),
    intended_use=(
        "Convert specific impulse in seconds to effective exhaust velocity "
        "for the ideal rocket equation; this is not lunar surface gravity."
    ),
    limitations=[
        "Conventional standard gravity used in the definition of specific impulse.",
        "Not the local gravitational acceleration at the Moon or any mission location.",
    ],
)


class IdealRocketEquationRequest(BaseModel):
    """Inputs must be individually traceable EngineeringValue records."""

    model_config = ConfigDict(extra="forbid")

    dry_mass: EngineeringValue
    propellant_mass: EngineeringValue
    specific_impulse: EngineeringValue
    intended_use: Annotated[str, Field(min_length=1, max_length=500)]

    @model_validator(mode="after")
    def inputs_must_match_equation_requirements(self) -> "IdealRocketEquationRequest":
        expected = (
            (self.dry_mass, "kg", Dimension.MASS, "dry_mass"),
            (self.propellant_mass, "kg", Dimension.MASS, "propellant_mass"),
            (self.specific_impulse, "s", Dimension.TIME, "specific_impulse"),
        )
        for value, unit, dimension, name in expected:
            if value.unit != unit or value.dimension != dimension:
                raise ValueError(f"{name} must use {unit} with dimension {dimension.value}")
            if value.value <= 0:
                raise ValueError(f"{name} must be greater than zero")

        value_ids = {
            self.dry_mass.value_id,
            self.propellant_mass.value_id,
            self.specific_impulse.value_id,
        }
        if len(value_ids) != 3:
            raise ValueError("Each input must have a unique value_id")
        return self


class IdealRocketEquationResult(BaseModel):
    """Calculated outputs retain input IDs, equation ID, model version and limits."""

    delta_v: EngineeringValue
    initial_mass: EngineeringValue
    mass_ratio: EngineeringValue
    input_values: list[EngineeringValue]
    constants: list[EngineeringValue]
    equation_id: str
    model_version: str
    equation_reference: str
    assumptions: list[str]
    limitations: list[str]


def calculate_ideal_delta_v(
    request: IdealRocketEquationRequest,
) -> IdealRocketEquationResult:
    """Calculate ideal delta-v; external forces and operational losses are excluded."""
    dry_mass = request.dry_mass.value
    propellant_mass = request.propellant_mass.value
    initial_mass = dry_mass + propellant_mass
    mass_ratio = initial_mass / dry_mass
    delta_v = request.specific_impulse.value * STANDARD_GRAVITY.value * log(mass_ratio)

    if not all(isfinite(value) for value in (initial_mass, mass_ratio, delta_v)):
        raise ValueError("Model output is outside the supported finite numeric range")

    assumptions = [
        "Effective exhaust velocity (specific impulse) is constant throughout the burn.",
        "All entered propellant mass is consumed; final mass equals entered dry mass.",
        "The ideal free-space rocket equation is used with no external forces.",
        "Standard gravity is used only to convert specific impulse to effective exhaust velocity.",
    ]
    limitations = [
        "Excludes lunar/planetary gravity losses, trajectory geometry and finite-burn steering losses.",
        "Excludes engine transients, throttling, pressure mismatch changes, residuals and trapped propellant.",
        "Does not include landing hazards, terrain, navigation, guidance, control or structural constraints.",
        "Ideal delta-v is not a mission delta-v budget, flight-performance prediction or safety result.",
        "This implementation is unvalidated and must not be used for flight or operational decisions.",
    ]

    def calculated_value(
        value_id: str,
        name: str,
        value: float,
        unit: str,
        dimension: Dimension,
        equation_id: str,
    ) -> EngineeringValue:
        return EngineeringValue(
            value_id=value_id,
            name=name,
            value=value,
            unit=unit,
            dimension=dimension,
            provenance=ProvenanceClass.CALCULATED,
            equation_id=equation_id,
            model_version=MODEL_VERSION,
            credibility=CredibilityStatus.UNVALIDATED,
            intended_use=request.intended_use,
            limitations=limitations,
        )

    return IdealRocketEquationResult(
        delta_v=calculated_value(
            "calculated.ideal_delta_v",
            "Ideal rocket-equation delta-v",
            delta_v,
            "m/s",
            Dimension.VELOCITY,
            DELTA_V_EQUATION_ID,
        ),
        initial_mass=calculated_value(
            "calculated.initial_mass",
            "Initial mass",
            initial_mass,
            "kg",
            Dimension.MASS,
            MASS_SUM_EQUATION_ID,
        ),
        mass_ratio=calculated_value(
            "calculated.mass_ratio",
            "Initial-to-final mass ratio",
            mass_ratio,
            "1",
            Dimension.DIMENSIONLESS,
            MASS_RATIO_EQUATION_ID,
        ),
        input_values=[request.dry_mass, request.propellant_mass, request.specific_impulse],
        constants=[STANDARD_GRAVITY],
        equation_id=DELTA_V_EQUATION_ID,
        model_version=MODEL_VERSION,
        equation_reference=(
            "https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/"
        ),
        assumptions=assumptions,
        limitations=limitations,
    )
