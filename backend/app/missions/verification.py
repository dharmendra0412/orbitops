"""Requirement verification evidence contracts."""
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.missions.projects import VerificationMethod


class VerificationOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class VerificationRecordCreate(BaseModel):
    """Evidence record for one requirement; it does not approve the mission."""

    model_config = ConfigDict(extra="forbid")

    requirement_id: Annotated[str, Field(min_length=1, max_length=100)]
    method: VerificationMethod
    outcome: VerificationOutcome
    performed_at: datetime
    performed_by: Annotated[str, Field(min_length=1, max_length=160)]
    summary: Annotated[str, Field(min_length=1, max_length=3000)]
    evidence_reference: Annotated[str, Field(min_length=1, max_length=1000)] | None = None


class VerificationRecord(VerificationRecordCreate):
    verification_id: UUID
    project_id: UUID
    recorded_at: datetime
