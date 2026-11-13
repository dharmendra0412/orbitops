"""Metadata contracts for traceable SPICE kernel artifact registration.

Registration stores user-declared metadata only. It does not download, hash,
parse, furnish, or scientifically validate a kernel.
"""
import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import uuid4

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
        "This metadata registration does not itself validate the uploaded artifact; acquisition and inspection evidence are stored separately.",
        "Coverage and frame metadata are descriptive and have not been checked against kernel contents.",
    ])


class SpiceKernelArtifactRecord(BaseModel):
    """Server-computed artifact digest and content-addressed storage reference."""

    model_config = ConfigDict(extra="forbid")

    kernel_id: str
    sha256: str
    size_bytes: int = Field(ge=0)
    storage_key: str
    acquired_at: datetime
    checksum_status: str = "matches_user_declared"
    limitations: list[str] = Field(default_factory=lambda: [
        "The digest was computed over the uploaded bytes and matches the registered user-declared digest.",
        "A matching user-declared digest does not independently authenticate the source or publisher.",
        "The artifact has not been parsed, furnished, or scientifically validated by a SPICE toolkit.",
    ])


class SpiceKernelInspectionRecord(BaseModel):
    """Immutable result of bounded CSPICE format and index inspection."""

    model_config = ConfigDict(extra="forbid")

    kernel_id: str
    artifact_sha256: str
    toolkit_name: str = "SpiceyPy"
    toolkit_version: str
    detected_architecture: str
    detected_kernel_type: str
    registration_type_matches: bool = True
    object_ids: list[int] = Field(default_factory=list)
    frame_class_ids: list[int] = Field(default_factory=list)
    coverage_intervals: list[dict[str, object]] = Field(default_factory=list)
    metadata_truncated: bool = False
    inspection_scope: str
    inspected_at: datetime
    inspection_status: str = "format_and_supported_index_inspected"
    limitations: list[str] = Field(default_factory=lambda: [
        "Inspection used CSPICE through a time-limited subprocess with best-effort POSIX resource limits; this is not a complete OS security sandbox.",
        "Only the kernel header and supported SPK, binary PCK, and DSK index metadata were inspected; text-kernel variables and meta-kernel paths were not loaded.",
        "SPK coverage intervals are reported as raw ET seconds past J2000 TDB; no time conversion was performed.",
        "Inspection does not authenticate the publisher, validate licence terms, or establish scientific suitability.",
        "The result is not independent scientific verification or mission acceptance evidence.",
    ])

class SpiceTimeConversionRecord(BaseModel):
    """Immutable UTC-to-ET result tied to the exact acquired LSK artifact."""

    model_config = ConfigDict(extra="forbid")

    conversion_id: str = Field(default_factory=lambda: uuid4().hex)
    kernel_id: str
    artifact_sha256: str
    toolkit_name: str = "SpiceyPy"
    toolkit_version: str
    input_utc: str | None = None
    input_et_seconds: float | None = None
    conversion_direction: str = "utc_to_et"
    et_seconds: float
    normalized_utc: str
    converted_at: datetime
    conversion_scope: str = "utc_to_et_using_single_registered_lsk"
    limitations: list[str] = Field(default_factory=lambda: [
        "Conversion used only the registered and acquired LSK artifact identified by artifact_sha256.",
        "The result depends on the leap-second table and time constants in that exact LSK; it may be stale for dates beyond its coverage.",
        "This is a time-system conversion, not ephemeris evaluation, frame transformation, or scientific validation.",
        "The subprocess has a timeout and best-effort POSIX resource limits, not a complete OS sandbox.",
    ])

class SpiceUtcToEtRequest(BaseModel):
    """UTC instant to convert using one explicitly selected LSK."""

    model_config = ConfigDict(extra="forbid")

    utc_time: Annotated[str, Field(min_length=5, max_length=128)]

    @field_validator("utc_time")
    @classmethod
    def utc_input_must_declare_utc(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.upper().endswith(" UTC"):
            raise ValueError("utc_time must end with an explicit UTC time-system suffix")
        return normalized


class SpiceEtToUtcRequest(BaseModel):
    """ET seconds past J2000 TDB to convert using one explicitly selected LSK."""

    model_config = ConfigDict(extra="forbid")

    et_seconds: Annotated[float, Field(allow_inf_nan=False)]
    precision: Annotated[int, Field(ge=0, le=6)] = 6


class SpiceFrameTransformRequest(BaseModel):
    """Position or state transformation through a single inspected fixed-frame FK."""

    model_config = ConfigDict(extra="forbid")

    from_frame: Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_+-]+$")]
    to_frame: Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_+-]+$")]
    et_seconds: Annotated[float, Field(allow_inf_nan=False)]
    transform_type: Literal["position", "state"] = "position"
    vector: list[Annotated[float, Field(allow_inf_nan=False)]] | None = None

    @model_validator(mode="after")
    def vector_dimension_must_match_transform(self) -> "SpiceFrameTransformRequest":
        if self.vector is not None:
            expected = 3 if self.transform_type == "position" else 6
            if len(self.vector) != expected:
                raise ValueError(f"{self.transform_type} vector must contain exactly {expected} values")
        return self


class SpiceFrameTransformRecord(BaseModel):
    """Immutable position/state frame transformation tied to one FK artifact."""

    model_config = ConfigDict(extra="forbid")

    transformation_id: str = Field(default_factory=lambda: uuid4().hex)
    kernel_id: str
    artifact_sha256: str
    toolkit_name: str = "SpiceyPy"
    toolkit_version: str
    from_frame: str
    to_frame: str
    et_seconds: float
    transform_type: Literal["position", "state"]
    matrix: list[list[float]]
    input_vector: list[float] | None = None
    output_vector: list[float] | None = None
    transformed_at: datetime
    transformation_scope: str = "single_inspected_text_fk_fixed_frame"
    limitations: list[str] = Field(default_factory=lambda: [
        "Only one acquired and inspected KPL/FK is loaded; no PCK, CK, SCLK, SPK, LSK, or meta-kernel is loaded.",
        "Only built-in inertial frames and fixed-offset FK frames (SPICE frame class 4) are supported.",
        "Dynamic, PCK body-fixed, CK spacecraft, switch, and time-dependent frames are rejected.",
        "The supplied epoch is ET seconds past J2000 TDB; UTC conversion is a separate operation using an explicit LSK.",
        "The worker has a timeout and best-effort POSIX resource limits, not a complete OS sandbox.",
        "A computed rotation is a geometric transformation, not scientific validation or mission acceptance.",
    ])
