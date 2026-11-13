"""Requirement-to-spacecraft allocation and traceability contracts."""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RequirementAllocationCreate(BaseModel):
    """Allocate a mission requirement to one spacecraft component."""

    model_config = ConfigDict(extra="forbid")

    requirement_id: Annotated[str, Field(min_length=1, max_length=100)]
    component_id: Annotated[str, Field(min_length=1, max_length=100)]
    rationale: Annotated[str, Field(min_length=1, max_length=2000)]
    allocated_by: Annotated[str, Field(min_length=1, max_length=160)]


class RequirementAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allocation_id: UUID
    project_id: UUID
    requirement_id: str
    component_id: str
    rationale: str
    allocated_by: str
    recorded_at: datetime


class RequirementTraceabilityRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    requirement_title: str
    requirement_statement: str
    requirement_category: str
    verification_method: str
    allocated: bool
    allocation_count: int
    allocations: list[RequirementAllocation]
    active_component_count: int
    stale_component_ids: list[str]
    verification_record_count: int
    pass_record_count: int
    fail_record_count: int
    inconclusive_record_count: int
    verification_evidence_present: bool


class RequirementTraceabilityMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    mission_revision: int
    spacecraft_configuration_revision: int | None
    requirement_count: int
    allocated_requirement_count: int
    unallocated_requirement_count: int
    rows: list[RequirementTraceabilityRow]
    limitations: list[str]
