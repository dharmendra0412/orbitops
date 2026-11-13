"""Small explicit unit registry for API-bound engineering quantities.

This registry checks declared dimensional categories. It does not perform
unit conversion or prove that a model's equations are dimensionally correct.
"""
from enum import StrEnum


class Dimension(StrEnum):
    DIMENSIONLESS = "dimensionless"
    LENGTH = "length"
    MASS = "mass"
    TIME = "time"
    TEMPERATURE = "temperature"
    VELOCITY = "velocity"
    GRAVITATIONAL_PARAMETER = "gravitational_parameter"
    ACCELERATION = "acceleration"
    FORCE = "force"
    PRESSURE = "pressure"
    POWER = "power"
    ENERGY = "energy"
    POWER_DENSITY = "power_density"
    DENSITY = "density"
    ANGLE = "angle"
    FREQUENCY = "frequency"
    DATA_RATE = "data_rate"
    DATA = "data"


UNIT_DIMENSIONS: dict[str, Dimension] = {
    "1": Dimension.DIMENSIONLESS,
    "m": Dimension.LENGTH,
    "km": Dimension.LENGTH,
    "kg": Dimension.MASS,
    "s": Dimension.TIME,
    "min": Dimension.TIME,
    "h": Dimension.TIME,
    "day": Dimension.TIME,
    "K": Dimension.TEMPERATURE,
    "degC": Dimension.TEMPERATURE,
    "m/s": Dimension.VELOCITY,
    "km/s": Dimension.VELOCITY,
    "m^3/s^2": Dimension.GRAVITATIONAL_PARAMETER,
    "km^3/s^2": Dimension.GRAVITATIONAL_PARAMETER,
    "m/s^2": Dimension.ACCELERATION,
    "N": Dimension.FORCE,
    "Pa": Dimension.PRESSURE,
    "kPa": Dimension.PRESSURE,
    "W": Dimension.POWER,
    "J": Dimension.ENERGY,
    "Wh": Dimension.ENERGY,
    "kWh": Dimension.ENERGY,
    "W/m^2": Dimension.POWER_DENSITY,
    "kg/m^3": Dimension.DENSITY,
    "rad": Dimension.ANGLE,
    "deg": Dimension.ANGLE,
    "Hz": Dimension.FREQUENCY,
    "bit/s": Dimension.DATA_RATE,
    "B": Dimension.DATA,
    "MB": Dimension.DATA,
    "GB": Dimension.DATA,
}


def unit_dimension(unit: str) -> Dimension | None:
    return UNIT_DIMENSIONS.get(unit)
