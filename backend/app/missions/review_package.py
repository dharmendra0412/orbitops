"""Consolidated mission engineering review package contracts."""
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.missions.project_evidence import MissionDatasetLink, MissionModelAssessmentLink
from app.missions.projects import MissionProjectRecord
from app.missions.spacecraft import (
    SpacecraftBudgetSummary,
    SpacecraftConfigurationRecord,
)
from app.missions.traceability import RequirementTraceabilityMatrix
from app.missions.verification import VerificationRecord


class ReviewPackageState(StrEnum):
    INCOMPLETE = "incomplete"
    REVIEW_REQUIRED = "review_required"
    EVIDENCE_COMPILED = "evidence_compiled"


class ReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["attention", "information"]
    title: str
    description: str


class ReviewPackageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_count: int = Field(ge=0)
    allocated_requirement_count: int = Field(ge=0)
    unallocated_requirement_count: int = Field(ge=0)
    requirements_without_evidence_count: int = Field(ge=0)
    verification_record_count: int = Field(ge=0)
    failed_verification_record_count: int = Field(ge=0)
    inconclusive_verification_record_count: int = Field(ge=0)
    stale_component_reference_count: int = Field(ge=0)
    spacecraft_component_count: int = Field(ge=0)
    linked_dataset_count: int = Field(ge=0)
    linked_model_assessment_count: int = Field(ge=0)


class MissionReviewPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_id: UUID
    generated_at: datetime
    project: MissionProjectRecord
    spacecraft_configuration: SpacecraftConfigurationRecord | None
    spacecraft_budget: SpacecraftBudgetSummary | None
    traceability_matrix: RequirementTraceabilityMatrix
    verification_records: list[VerificationRecord]
    linked_datasets: list[MissionDatasetLink]
    linked_model_assessments: list[MissionModelAssessmentLink]
    summary: ReviewPackageSummary
    review_state: ReviewPackageState
    findings: list[ReviewFinding]
    limitations: list[str]
