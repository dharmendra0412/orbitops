"""Dataset ingestion manifest contracts.

These models validate metadata structure and file identity fields. They do not
download, authenticate, decode, or scientifically assess a dataset.
"""
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class AccessClassification(StrEnum):
    PUBLIC = "public"
    REGISTRATION_REQUIRED = "registration_required"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class DatasetManifest(BaseModel):
    """Traceable metadata for one immutable source data product or file."""

    model_config = ConfigDict(extra="forbid")

    manifest_id: Annotated[str, Field(min_length=1, max_length=120)]
    title: Annotated[str, Field(min_length=1, max_length=300)]
    provider: Annotated[str, Field(min_length=1, max_length=160)]
    product_id: Annotated[str, Field(min_length=1, max_length=160)]
    release_or_version: Annotated[str, Field(min_length=1, max_length=120)]
    source_url: HttpUrl
    retrieved_at: datetime
    file_name: Annotated[str, Field(min_length=1, max_length=255)]
    media_type: Annotated[str, Field(min_length=1, max_length=120)]
    data_format: Annotated[str, Field(min_length=1, max_length=80)]
    file_size_bytes: Annotated[int, Field(gt=0)]
    checksum_sha256: Annotated[str, Field(pattern=r"^[0-9a-fA-F]{64}$")]
    license_or_terms: Annotated[str, Field(min_length=1, max_length=300)]
    access_classification: AccessClassification
    coordinate_reference_frame: Annotated[str, Field(min_length=1, max_length=160)] | None = None
    time_system: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    temporal_coverage_start: datetime | None = None
    temporal_coverage_end: datetime | None = None
    variable_units: dict[
        Annotated[str, Field(min_length=1, max_length=120)],
        Annotated[str, Field(min_length=1, max_length=40)],
    ] = Field(default_factory=dict)
    notes: Annotated[str, Field(max_length=2000)] | None = None

    @field_validator("file_name")
    @classmethod
    def file_name_must_be_a_name_not_a_path(cls, value: str) -> str:
        if "/" in value or "\\" in value or value in {".", ".."}:
            raise ValueError("file_name must not contain a directory path")
        return value

    @model_validator(mode="after")
    def temporal_coverage_must_be_ordered(self) -> "DatasetManifest":
        start = self.temporal_coverage_start
        end = self.temporal_coverage_end
        if start is not None and end is not None:
            if start.tzinfo != end.tzinfo:
                raise ValueError("Temporal coverage endpoints must use compatible time zones")
            if end <= start:
                raise ValueError("temporal_coverage_end must be later than start")
        return self
