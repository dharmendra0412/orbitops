"""Two-body Keplerian orbital mechanics calculators.

These models are analytical prototypes. They do not propagate trajectories,
consume ephemerides, or establish mission feasibility.
"""
from datetime import datetime
from math import isfinite, pi, sqrt
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engineering.provenance import (
    CredibilityStatus,
    EngineeringValue,
    ProvenanceClass,
)
from app.engineering.units import Dimension

MODEL_ID = "orbital.two-body-keplerian"
MODEL_VERSION = "0.1.0"
CIRCULAR_VELOCITY_EQUATION_ID = "ORBITAL.CIRCULAR_VELOCITY.V1"
VIS_VIVA_EQUATION_ID = "ORBITAL.VIS_VIVA.V1"
ORBITAL_PERIOD_EQUATION_ID = "ORBITAL.PERIOD.V1"
ESCAPE_VELOCITY_EQUATION_ID = "ORBITAL.ESCAPE_VELOCITY.V1"
HOHMANN_DELTA_V_EQUATION_ID = "ORBITAL.HOHMANN.TRANSFER_DELTA_V.V1"
HOHMANN_TIME_EQUATION_ID = "ORBITAL.HOHMANN.TRANSFER_TIME.V1"
HOHMANN_SEMIMAJOR_AXIS_EQUATION_ID = "ORBITAL.HOHMANN.TRANSFER_SEMIMAJOR_AXIS.V1"

COMMON_LIMITATIONS = [
    "Uses a two-body point-mass gravitational model with a fixed central-body gravitational parameter.",
    "Excludes third-body perturbations, oblateness, solar radiation pressure, drag, and other non-Keplerian forces.",
    "Does not use ephemerides, solve launch windows, propagate a trajectory, or model navigation/estimation errors.",
    "Outputs are unvalidated analytical estimates and are not flight-performance or operational-safety results.",
]


def _validate_quantity(value: EngineeringValue, name: str, unit: str, dimension: Dimension) -> None:
    if value.unit != unit or value.dimension != dimension:
        raise ValueError(f"{name} must use {unit} with dimension {dimension.value}")
    if value.value <= 0:
        raise ValueError(f"{name} must be greater than zero")


def _validate_unique_value_ids(values: list[EngineeringValue]) -> None:
    ids = [item.value_id for item in values]
    if len(ids) != len(set(ids)):
        raise ValueError("Each input must have a unique value_id")


def _calculated_value(
    value_id: str,
    name: str,
    value: float,
    unit: str,
    dimension: Dimension,
    equation_id: str,
    intended_use: str,
) -> EngineeringValue:
    if not isfinite(value):
        raise ValueError("Orbital model output is outside the supported finite numeric range")
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
        intended_use=intended_use,
        limitations=COMMON_LIMITATIONS,
    )


class OrbitalMechanicsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gravitational_parameter: EngineeringValue
    intended_use: Annotated[str, Field(min_length=1, max_length=500)]

    @model_validator(mode="after")
    def validate_mu(self) -> "OrbitalMechanicsRequest":
        _validate_quantity(
            self.gravitational_parameter,
            "gravitational_parameter",
            "m^3/s^2",
            Dimension.GRAVITATIONAL_PARAMETER,
        )
        return self


class CircularOrbitRequest(OrbitalMechanicsRequest):
    orbital_radius: EngineeringValue

    @model_validator(mode="after")
    def validate_radius(self) -> "CircularOrbitRequest":
        _validate_quantity(self.orbital_radius, "orbital_radius", "m", Dimension.LENGTH)
        _validate_unique_value_ids([self.gravitational_parameter, self.orbital_radius])
        return self


class VisVivaRequest(OrbitalMechanicsRequest):
    orbital_radius: EngineeringValue
    semi_major_axis: EngineeringValue

    @model_validator(mode="after")
    def validate_orbit(self) -> "VisVivaRequest":
        _validate_quantity(self.orbital_radius, "orbital_radius", "m", Dimension.LENGTH)
        _validate_quantity(self.semi_major_axis, "semi_major_axis", "m", Dimension.LENGTH)
        _validate_unique_value_ids(
            [self.gravitational_parameter, self.orbital_radius, self.semi_major_axis]
        )
        if 2.0 / self.orbital_radius.value - 1.0 / self.semi_major_axis.value <= 0:
            raise ValueError("Inputs do not describe a real-valued bound elliptical-orbit speed")
        return self


class OrbitalPeriodRequest(OrbitalMechanicsRequest):
    semi_major_axis: EngineeringValue

    @model_validator(mode="after")
    def validate_axis(self) -> "OrbitalPeriodRequest":
        _validate_quantity(self.semi_major_axis, "semi_major_axis", "m", Dimension.LENGTH)
        _validate_unique_value_ids([self.gravitational_parameter, self.semi_major_axis])
        return self


class EscapeVelocityRequest(OrbitalMechanicsRequest):
    orbital_radius: EngineeringValue

    @model_validator(mode="after")
    def validate_radius(self) -> "EscapeVelocityRequest":
        _validate_quantity(self.orbital_radius, "orbital_radius", "m", Dimension.LENGTH)
        _validate_unique_value_ids([self.gravitational_parameter, self.orbital_radius])
        return self


class HohmannTransferRequest(OrbitalMechanicsRequest):
    initial_orbit_radius: EngineeringValue
    target_orbit_radius: EngineeringValue

    @model_validator(mode="after")
    def validate_transfer(self) -> "HohmannTransferRequest":
        _validate_quantity(
            self.initial_orbit_radius, "initial_orbit_radius", "m", Dimension.LENGTH
        )
        _validate_quantity(
            self.target_orbit_radius, "target_orbit_radius", "m", Dimension.LENGTH
        )
        _validate_unique_value_ids(
            [
                self.gravitational_parameter,
                self.initial_orbit_radius,
                self.target_orbit_radius,
            ]
        )
        if self.initial_orbit_radius.value == self.target_orbit_radius.value:
            raise ValueError("Initial and target orbit radii must differ for a Hohmann transfer")
        return self


class OrbitalScalarResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: EngineeringValue
    input_values: list[EngineeringValue]
    equation_id: str
    model_id: str = MODEL_ID
    model_version: str = MODEL_VERSION
    assumptions: list[str]
    limitations: list[str]
    run_id: str | None = None
    created_at: datetime | None = None


class HohmannTransferResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transfer_delta_v: EngineeringValue
    first_burn_delta_v: EngineeringValue
    second_burn_delta_v: EngineeringValue
    transfer_time: EngineeringValue
    transfer_semi_major_axis: EngineeringValue
    initial_circular_velocity: EngineeringValue
    target_circular_velocity: EngineeringValue
    transfer_velocity_at_initial_orbit: EngineeringValue
    transfer_velocity_at_target_orbit: EngineeringValue
    input_values: list[EngineeringValue]
    equation_ids: list[str]
    model_id: str = MODEL_ID
    model_version: str = MODEL_VERSION
    assumptions: list[str]
    limitations: list[str]
    run_id: str | None = None
    created_at: datetime | None = None


def calculate_circular_velocity(request: CircularOrbitRequest) -> OrbitalScalarResult:
    mu = request.gravitational_parameter.value
    radius = request.orbital_radius.value
    velocity = sqrt(mu / radius)
    return OrbitalScalarResult(
        output=_calculated_value(
            "orbital.circular_velocity",
            "Circular orbital velocity",
            velocity,
            "m/s",
            Dimension.VELOCITY,
            CIRCULAR_VELOCITY_EQUATION_ID,
            request.intended_use,
        ),
        input_values=[request.gravitational_parameter, request.orbital_radius],
        equation_id=CIRCULAR_VELOCITY_EQUATION_ID,
        assumptions=["The orbit is circular and the central body is represented by a point mass."],
        limitations=COMMON_LIMITATIONS,
    )


def calculate_vis_viva_speed(request: VisVivaRequest) -> OrbitalScalarResult:
    mu = request.gravitational_parameter.value
    radius = request.orbital_radius.value
    semi_major_axis = request.semi_major_axis.value
    speed_squared = mu * (2.0 / radius - 1.0 / semi_major_axis)
    if speed_squared <= 0:
        raise ValueError("Vis-viva speed squared must be positive")
    return OrbitalScalarResult(
        output=_calculated_value(
            "orbital.vis_viva_speed",
            "Vis-viva orbital speed",
            sqrt(speed_squared),
            "m/s",
            Dimension.VELOCITY,
            VIS_VIVA_EQUATION_ID,
            request.intended_use,
        ),
        input_values=[
            request.gravitational_parameter,
            request.orbital_radius,
            request.semi_major_axis,
        ],
        equation_id=VIS_VIVA_EQUATION_ID,
        assumptions=["The orbit is a bound Keplerian ellipse with positive semi-major axis."],
        limitations=COMMON_LIMITATIONS,
    )


def calculate_orbital_period(request: OrbitalPeriodRequest) -> OrbitalScalarResult:
    mu = request.gravitational_parameter.value
    semi_major_axis = request.semi_major_axis.value
    period = 2.0 * pi * sqrt(semi_major_axis**3 / mu)
    return OrbitalScalarResult(
        output=_calculated_value(
            "orbital.period",
            "Keplerian orbital period",
            period,
            "s",
            Dimension.TIME,
            ORBITAL_PERIOD_EQUATION_ID,
            request.intended_use,
        ),
        input_values=[request.gravitational_parameter, request.semi_major_axis],
        equation_id=ORBITAL_PERIOD_EQUATION_ID,
        assumptions=["The orbit is a Keplerian two-body orbit with a fixed semi-major axis."],
        limitations=COMMON_LIMITATIONS,
    )


def calculate_escape_velocity(request: EscapeVelocityRequest) -> OrbitalScalarResult:
    mu = request.gravitational_parameter.value
    radius = request.orbital_radius.value
    velocity = sqrt(2.0 * mu / radius)
    return OrbitalScalarResult(
        output=_calculated_value(
            "orbital.escape_velocity",
            "Local two-body escape velocity",
            velocity,
            "m/s",
            Dimension.VELOCITY,
            ESCAPE_VELOCITY_EQUATION_ID,
            request.intended_use,
        ),
        input_values=[request.gravitational_parameter, request.orbital_radius],
        equation_id=ESCAPE_VELOCITY_EQUATION_ID,
        assumptions=["Escape is evaluated from the specified radius in a two-body point-mass field."],
        limitations=COMMON_LIMITATIONS,
    )


def calculate_hohmann_transfer(request: HohmannTransferRequest) -> HohmannTransferResult:
    mu = request.gravitational_parameter.value
    r1 = request.initial_orbit_radius.value
    r2 = request.target_orbit_radius.value
    transfer_axis = (r1 + r2) / 2.0
    initial_circular = sqrt(mu / r1)
    target_circular = sqrt(mu / r2)
    transfer_initial = sqrt(mu * (2.0 / r1 - 1.0 / transfer_axis))
    transfer_target = sqrt(mu * (2.0 / r2 - 1.0 / transfer_axis))
    first_burn = abs(transfer_initial - initial_circular)
    second_burn = abs(target_circular - transfer_target)
    total_delta_v = first_burn + second_burn
    transfer_time = pi * sqrt(transfer_axis**3 / mu)
    use = request.intended_use
    return HohmannTransferResult(
        transfer_delta_v=_calculated_value(
            "orbital.hohmann.total_delta_v",
            "Total ideal Hohmann transfer delta-v",
            total_delta_v,
            "m/s",
            Dimension.VELOCITY,
            HOHMANN_DELTA_V_EQUATION_ID,
            use,
        ),
        first_burn_delta_v=_calculated_value(
            "orbital.hohmann.first_burn_delta_v",
            "First ideal Hohmann transfer burn delta-v",
            first_burn,
            "m/s",
            Dimension.VELOCITY,
            HOHMANN_DELTA_V_EQUATION_ID,
            use,
        ),
        second_burn_delta_v=_calculated_value(
            "orbital.hohmann.second_burn_delta_v",
            "Second ideal Hohmann transfer burn delta-v",
            second_burn,
            "m/s",
            Dimension.VELOCITY,
            HOHMANN_DELTA_V_EQUATION_ID,
            use,
        ),
        transfer_time=_calculated_value(
            "orbital.hohmann.transfer_time",
            "Ideal Hohmann transfer time",
            transfer_time,
            "s",
            Dimension.TIME,
            HOHMANN_TIME_EQUATION_ID,
            use,
        ),
        transfer_semi_major_axis=_calculated_value(
            "orbital.hohmann.transfer_semi_major_axis",
            "Hohmann transfer ellipse semi-major axis",
            transfer_axis,
            "m",
            Dimension.LENGTH,
            HOHMANN_SEMIMAJOR_AXIS_EQUATION_ID,
            use,
        ),
        initial_circular_velocity=_calculated_value(
            "orbital.hohmann.initial_circular_velocity",
            "Initial circular orbit velocity",
            initial_circular,
            "m/s",
            Dimension.VELOCITY,
            CIRCULAR_VELOCITY_EQUATION_ID,
            use,
        ),
        target_circular_velocity=_calculated_value(
            "orbital.hohmann.target_circular_velocity",
            "Target circular orbit velocity",
            target_circular,
            "m/s",
            Dimension.VELOCITY,
            CIRCULAR_VELOCITY_EQUATION_ID,
            use,
        ),
        transfer_velocity_at_initial_orbit=_calculated_value(
            "orbital.hohmann.transfer_velocity_at_initial",
            "Transfer ellipse velocity at initial orbit",
            transfer_initial,
            "m/s",
            Dimension.VELOCITY,
            VIS_VIVA_EQUATION_ID,
            use,
        ),
        transfer_velocity_at_target_orbit=_calculated_value(
            "orbital.hohmann.transfer_velocity_at_target",
            "Transfer ellipse velocity at target orbit",
            transfer_target,
            "m/s",
            Dimension.VELOCITY,
            VIS_VIVA_EQUATION_ID,
            use,
        ),
        input_values=[
            request.gravitational_parameter,
            request.initial_orbit_radius,
            request.target_orbit_radius,
        ],
        equation_ids=[
            HOHMANN_DELTA_V_EQUATION_ID,
            HOHMANN_TIME_EQUATION_ID,
            HOHMANN_SEMIMAJOR_AXIS_EQUATION_ID,
        ],
        assumptions=[
            "Initial and target orbits are circular and coplanar about the same central body.",
            "The transfer is an ideal impulsive two-burn Hohmann transfer.",
            "The central body is represented by a point mass with constant gravitational parameter.",
        ],
        limitations=COMMON_LIMITATIONS + [
            "Does not model departure/arrival phase angles, launch windows, planetary ephemerides, or Lambert targeting.",
            "Does not include plane changes, finite-duration burns, parking-orbit injection, capture, or gravity assists.",
            "Transfer delta-v is not a complete mission delta-v budget.",
        ],
    )
