"""Project-scoped links to dataset manifests and model assessment evidence."""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ingestion.manifests import DatasetManifest
from app.missions.model_governance import ModelAssessment


class MissionDatasetLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_id: Annotated[str, Field(min_length=1, max_length=120)]
    purpose: Annotated[str, Field(min_length=5, max_length=2000)]
    linked_by: Annotated[str, Field(min_length=1, max_length=160)]


class MissionDatasetLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_id: UUID
    project_id: UUID
    manifest: DatasetManifest
    purpose: str
    linked_by: str
    linked_at: datetime


class MissionModelAssessmentLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: UUID
    rationale: Annotated[str, Field(min_length=5, max_length=2000)]
    linked_by: Annotated[str, Field(min_length=1, max_length=160)]


class MissionModelAssessmentLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_id: UUID
    project_id: UUID
    assessment: ModelAssessment
    rationale: str
    linked_by: str
    linked_at: datetime
