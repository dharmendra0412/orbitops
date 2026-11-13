"""Model verification and validation evidence contracts."""
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelAssessmentKind(StrEnum):
    VERIFICATION = "verification"
    VALIDATION = "validation"


class ModelAssessmentOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class ModelAssessmentMethod(StrEnum):
    ANALYSIS = "analysis"
    TEST = "test"
    COMPARISON = "comparison"
    INSPECTION = "inspection"
    DEMONSTRATION = "demonstration"


class ModelCredibilityState(StrEnum):
    UNVALIDATED = "unvalidated"
    VERIFIED = "verified"
    VALIDATED = "validated"
    REVIEW_REQUIRED = "review_required"


class ModelDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    display_name: str
    model_version: str
    equation_ids: list[str]
    intended_scope: str
    current_state: ModelCredibilityState
    latest_verification_outcome: ModelAssessmentOutcome | None = None
    latest_validation_outcome: ModelAssessmentOutcome | None = None
    assessment_count: int = Field(ge=0)


class ModelAssessmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: Annotated[str, Field(min_length=1, max_length=160)]
    model_version: Annotated[str, Field(min_length=1, max_length=80)]
    equation_id: Annotated[str, Field(min_length=1, max_length=160)]
    kind: ModelAssessmentKind
    outcome: ModelAssessmentOutcome
    method: ModelAssessmentMethod
    performed_at: datetime
    performed_by: Annotated[str, Field(min_length=1, max_length=160)]
    summary: Annotated[str, Field(min_length=10, max_length=4000)]
    evidence_reference: Annotated[str, Field(min_length=1, max_length=1000)]
    reference_dataset_id: Annotated[str, Field(min_length=1, max_length=160)] | None = None


class ModelAssessment(ModelAssessmentCreate):
    assessment_id: UUID
    recorded_at: datetime


class ModelGovernanceCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    models: list[ModelDefinition]
    limitations: list[str]
