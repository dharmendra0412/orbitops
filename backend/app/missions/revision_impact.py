"""Historical mission and spacecraft revision change-impact contracts."""
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RevisionChangeType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class RequirementRevisionChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    change_type: RevisionChangeType
    baseline_title: str | None = None
    target_title: str | None = None
    changed_fields: list[str] = Field(default_factory=list)


class ComponentRevisionChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: str
    change_type: RevisionChangeType
    baseline_name: str | None = None
    target_name: str | None = None
    baseline_subsystem: str | None = None
    target_subsystem: str | None = None
    changed_fields: list[str] = Field(default_factory=list)


class AllocationImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allocation_id: UUID
    requirement_id: str
    component_id: str
    impact_reasons: list[str]


class RevisionChangeImpactReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    baseline_mission_revision: int
    target_mission_revision: int
    baseline_spacecraft_revision: int
    target_spacecraft_revision: int
    requirement_changes: list[RequirementRevisionChange]
    component_changes: list[ComponentRevisionChange]
    impacted_allocations: list[AllocationImpact]
    added_requirement_count: int
    removed_requirement_count: int
    modified_requirement_count: int
    added_component_count: int
    removed_component_count: int
    modified_component_count: int
    limitations: list[str]


class RevisionImpactQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_mission_revision: Annotated[int, Field(ge=1)]
    target_mission_revision: Annotated[int, Field(ge=1)]
    baseline_spacecraft_revision: Annotated[int, Field(ge=1)]
    target_spacecraft_revision: Annotated[int, Field(ge=1)]
