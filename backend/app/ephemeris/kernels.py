"""Metadata contracts for traceable SPICE kernel artifact registration.

Registration stores user-declared metadata only. It does not download, hash,
parse, furnish, or scientifically validate a kernel.
"""
import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class SpiceKernelType(StrEnum):
    SPK = "SPK"
    PCK = "PCK"
    LSK = "LSK"
    FK = "FK"
    IK = "IK"
    SCLK = "SCLK"
    DSK = "DSK"
    MK = "MK"


class SpiceKernelRegistration(BaseModel):
    """User-supplied identity and coverage metadata for one kernel artifact."""

    model_config = ConfigDict(extra="forbid")

    kernel_id: Annotated[str, Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]
    file_name: Annotated[str, Field(min_length=1, max_length=255)]
    kernel_type: SpiceKernelType
    source_url: HttpUrl
    provider: Annotated[str, Field(min_length=1, max_length=160)]
    release_or_version: Annotated[str, Field(min_length=1, max_length=120)]
    sha256: Annotated[str, Field(min_length=64, max_length=64)]
    coverage_start: datetime | None = None
    coverage_end: datetime | None = None
    time_system: Annotated[str, Field(min_length=1, max_length=40)] = "TDB"
    reference_frames: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(default_factory=list)
    target_names: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(default_factory=list)
    license_or_terms: Annotated[str, Field(min_length=1, max_length=500)]
    notes: Annotated[str, Field(min_length=1, max_length=1000)] | None = None

    @field_validator("sha256")
    @classmethod
    def sha256_must_be_hex(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must contain exactly 64 hexadecimal characters")
        return value.lower()

    @field_validator("file_name")
    @classmethod
    def file_name_must_be_plain(cls, value: str) -> str:
        if "/" in value or "\\" in value or value in {".", ".."}:
            raise ValueError("file_name must be a plain file name")
        return value

    @model_validator(mode="after")
    def coverage_must_be_ordered_and_timezone_aware(self) -> "SpiceKernelRegistration":
        if (self.coverage_start is None) != (self.coverage_end is None):
            raise ValueError("coverage_start and coverage_end must be supplied together")
        if self.coverage_start is not None and self.coverage_end is not None:
            if self.coverage_start.utcoffset() is None or self.coverage_end.utcoffset() is None:
                raise ValueError("coverage timestamps must include a timezone")
            if self.coverage_end <= self.coverage_start:
                raise ValueError("coverage_end must be later than coverage_start")
        return self


class SpiceKernelRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registration: SpiceKernelRegistration
    registered_at: datetime
    metadata_status: str = "user_declared_unverified"
    limitations: list[str] = Field(default_factory=lambda: [
        "The SHA-256 value is user-declared and has not been computed by ORBITOPS.",
        "The source URL and licence/terms have not been independently authenticated.",
        "The kernel artifact has not been downloaded, parsed, furnished, or validated.",
        "Coverage and frame metadata are descriptive and have not been checked against kernel contents.",
    ])
