"""Mission project and requirements contracts.

These records capture engineering intent. They do not assert mission feasibility.
"""
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RequirementCategory(StrEnum):
    SCIENCE = "science"
    MISSION = "mission"
    MASS = "mass"
    POWER = "power"
    THERMAL = "thermal"
    COMMUNICATIONS = "communications"
    NAVIGATION = "navigation"
    ENVIRONMENT = "environment"
    OPERATIONS = "operations"
    SAFETY = "safety"
    VERIFICATION = "verification"


class VerificationMethod(StrEnum):
    ANALYSIS = "analysis"
    TEST = "test"
    INSPECTION = "inspection"
    DEMONSTRATION = "demonstration"
    TBD = "to_be_defined"


class MissionRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: Annotated[str, Field(min_length=1, max_length=100)]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    statement: Annotated[str, Field(min_length=1, max_length=2000)]
    category: RequirementCategory
    verification_method: VerificationMethod = VerificationMethod.TBD
    acceptance_criteria: Annotated[str, Field(min_length=1, max_length=2000)]
    source_reference: Annotated[str, Field(max_length=500)] | None = None


class MissionProjectDraft(BaseModel):
    """A user-authored mission definition with explicit scope and requirements."""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=3, max_length=160)]
    summary: Annotated[str, Field(min_length=1, max_length=2000)]
    target_body: Annotated[str, Field(min_length=2, max_length=100)]
    mission_archetype: Annotated[str, Field(min_length=2, max_length=100)]
    primary_objective: Annotated[str, Field(min_length=10, max_length=4000)]
    intended_users: Annotated[list[str], Field(max_length=20)] = Field(default_factory=list)
    requirements: Annotated[list[MissionRequirement], Field(max_length=200)] = Field(default_factory=list)


class MissionProjectRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: UUID
    project_id: UUID
    revision_number: int = Field(ge=1)
    created_at: datetime
    draft: MissionProjectDraft


class MissionProjectRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    name: str
    target_body: str
    mission_archetype: str
    created_at: datetime
    updated_at: datetime
    latest_revision: int = Field(ge=1)
    revision: MissionProjectRevision


class MissionProjectSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    name: str
    target_body: str
    mission_archetype: str
    created_at: datetime
    updated_at: datetime
    latest_revision: int = Field(ge=1)
