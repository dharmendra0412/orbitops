"""Spacecraft configuration contracts and transparent budget calculations."""
from enum import StrEnum
from math import isfinite
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engineering.provenance import EngineeringValue
from app.engineering.units import Dimension


class SpacecraftSubsystem(StrEnum):
    STRUCTURE = "structure"
    PROPULSION = "propulsion"
    POWER = "power"
    THERMAL = "thermal"
    AVIONICS = "avionics"
    COMMUNICATIONS = "communications"
    GUIDANCE_NAVIGATION_CONTROL = "guidance_navigation_control"
    PAYLOAD = "payload"
    MECHANISMS = "mechanisms"
    OTHER = "other"


class SpacecraftComponent(BaseModel):
    """One configuration item; all numerical engineering values retain provenance."""

    model_config = ConfigDict(extra="forbid")

    component_id: Annotated[str, Field(min_length=1, max_length=100)]
    name: Annotated[str, Field(min_length=1, max_length=160)]
    subsystem: SpacecraftSubsystem
    manufacturer: Annotated[str, Field(max_length=160)] | None = None
    model: Annotated[str, Field(max_length=160)] | None = None
    mass: EngineeringValue
    power_draw: EngineeringValue | None = None
    power_generation: EngineeringValue | None = None
    load_duty_cycle: float = Field(ge=0.0, le=1.0)
    generation_duty_cycle: float = Field(ge=0.0, le=1.0)
    notes: Annotated[str, Field(max_length=2000)] | None = None

    @model_validator(mode="after")
    def validate_dimensions(self) -> "SpacecraftComponent":
        if self.mass.dimension != Dimension.MASS or self.mass.unit != "kg":
            raise ValueError("Component mass must use kg and the mass dimension")
        if self.mass.value < 0:
            raise ValueError("Component mass cannot be negative")
        for label, quantity in (
            ("power_draw", self.power_draw),
            ("power_generation", self.power_generation),
        ):
            if quantity is not None:
                if quantity.dimension != Dimension.POWER or quantity.unit != "W":
                    raise ValueError(f"{label} must use W and the power dimension")
                if quantity.value < 0:
                    raise ValueError(f"{label} cannot be negative")
        return self


class SpacecraftConfigurationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=3, max_length=160)]
    description: Annotated[str, Field(min_length=1, max_length=2000)]
    components: Annotated[list[SpacecraftComponent], Field(max_length=500)] = Field(default_factory=list)
    mass_margin_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    assumptions: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_component_ids(self) -> "SpacecraftConfigurationDraft":
        ids = [item.component_id for item in self.components]
        if len(ids) != len(set(ids)):
            raise ValueError("Component IDs must be unique within a configuration revision")
        return self


class SpacecraftConfigurationRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: UUID
    project_id: UUID
    revision_number: int = Field(ge=1)
    draft: SpacecraftConfigurationDraft
    created_at: str


class SpacecraftConfigurationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configuration_id: UUID
    project_id: UUID
    latest_revision: int = Field(ge=1)
    revision: SpacecraftConfigurationRevision


class MassBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_mass_kg: float
    margin_percent: float
    margin_mass_kg: float
    total_with_margin_kg: float
    component_count: int


class PowerBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    average_generation_w: float
    average_load_w: float
    net_power_w: float
    component_count: int
    assumptions: list[str]


class SpacecraftBudgetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configuration_id: UUID
    project_id: UUID
    revision_number: int
    mass: MassBudget
    power: PowerBudget


def calculate_budgets(record: SpacecraftConfigurationRecord) -> SpacecraftBudgetSummary:
    """Calculate bookkeeping totals; this is not a validated spacecraft simulation."""
    draft = record.revision.draft
    mass_kg = sum(component.mass.value for component in draft.components)
    margin_kg = mass_kg * draft.mass_margin_percent / 100.0
    generation_w = sum(
        component.power_generation.value * component.generation_duty_cycle
        for component in draft.components
        if component.power_generation is not None
    )
    load_w = sum(
        component.power_draw.value * component.load_duty_cycle
        for component in draft.components
        if component.power_draw is not None
    )
    if not all(isfinite(value) for value in (mass_kg, margin_kg, generation_w, load_w)):
        raise ValueError("Budget totals must be finite")
    return SpacecraftBudgetSummary(
        configuration_id=record.configuration_id,
        project_id=record.project_id,
        revision_number=record.latest_revision,
        mass=MassBudget(
            component_mass_kg=mass_kg,
            margin_percent=draft.mass_margin_percent,
            margin_mass_kg=margin_kg,
            total_with_margin_kg=mass_kg + margin_kg,
            component_count=len(draft.components),
        ),
        power=PowerBudget(
            average_generation_w=generation_w,
            average_load_w=load_w,
            net_power_w=generation_w - load_w,
            component_count=len(draft.components),
            assumptions=[
                "Power values are average component-level values multiplied by user-declared duty cycles.",
                "No battery, eclipse, transient, degradation, conversion-loss or thermal coupling model is applied.",
                "Mass margin is a user-entered percentage applied to the sum of component masses.",
            ],
        ),
    )
