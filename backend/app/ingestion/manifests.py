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


class AssetStage(StrEnum):
    SOURCE = "source"
    TRANSFORMED = "transformed"
    DERIVED = "derived"


class DatasetManifest(BaseModel):
    """Traceable metadata for one immutable source data product or file."""

    model_config = ConfigDict(extra="forbid")

    manifest_id: Annotated[str, Field(min_length=1, max_length=120)]
    title: Annotated[str, Field(min_length=1, max_length=300)]
    provider: Annotated[str, Field(min_length=1, max_length=160)]
    product_id: Annotated[str, Field(min_length=1, max_length=160)]
    release_or_version: Annotated[str, Field(min_length=1, max_length=120)]
    source_url: HttpUrl
    citation_text: Annotated[str, Field(min_length=1, max_length=1000)]
    retrieved_at: datetime
    file_name: Annotated[str, Field(min_length=1, max_length=255)]
    media_type: Annotated[str, Field(min_length=1, max_length=120)]
    data_format: Annotated[str, Field(min_length=1, max_length=80)]
    file_size_bytes: Annotated[int, Field(gt=0)]
    checksum_sha256: Annotated[str, Field(pattern=r"^[0-9a-fA-F]{64}$")]
    license_or_terms: Annotated[str, Field(min_length=1, max_length=300)]
    access_classification: AccessClassification
    asset_stage: AssetStage = AssetStage.SOURCE
    property_or_asset: Annotated[str, Field(min_length=1, max_length=160)] | None = None
    original_units: dict[
        Annotated[str, Field(min_length=1, max_length=120)],
        Annotated[str, Field(min_length=1, max_length=40)],
    ] = Field(default_factory=dict)
    transformation: Annotated[str, Field(min_length=1, max_length=1000)] | None = None
    transform_version: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    coordinate_reference_frame: Annotated[str, Field(min_length=1, max_length=160)] | None = None
    time_system: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    temporal_coverage_start: datetime | None = None
    temporal_coverage_end: datetime | None = None
    spatial_resolution_value: Annotated[float, Field(gt=0)] | None = None
    spatial_resolution_unit: Annotated[str, Field(min_length=1, max_length=40)] | None = None
    variable_units: dict[
        Annotated[str, Field(min_length=1, max_length=120)],
        Annotated[str, Field(min_length=1, max_length=40)],
    ] = Field(default_factory=dict)
    uncertainty_or_quality: Annotated[str, Field(min_length=1, max_length=1000)] | None = None
    limitations: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        default_factory=list
    )
    notes: Annotated[str, Field(max_length=2000)] | None = None

    @field_validator("file_name")
    @classmethod
    def file_name_must_be_a_name_not_a_path(cls, value: str) -> str:
        if "/" in value or "\\" in value or value in {".", ".."}:
            raise ValueError("file_name must not contain a directory path")
        return value

    @model_validator(mode="after")
    def metadata_must_be_consistent(self) -> "DatasetManifest":
        start = self.temporal_coverage_start
        end = self.temporal_coverage_end
        if start is not None and end is not None:
            start_is_aware = start.utcoffset() is not None
            end_is_aware = end.utcoffset() is not None
            if start_is_aware != end_is_aware:
                raise ValueError("Temporal coverage endpoints must both be timezone-aware or naive")
            if end <= start:
                raise ValueError("temporal_coverage_end must be later than start")

        if bool(self.transformation) != bool(self.transform_version):
            raise ValueError("transformation and transform_version must be supplied together")
        if self.asset_stage != AssetStage.SOURCE and not self.transformation:
            raise ValueError("Transformed and derived assets require transformation metadata")
        if (self.spatial_resolution_value is None) != (self.spatial_resolution_unit is None):
            raise ValueError("Spatial resolution value and unit must be supplied together")
        return self
