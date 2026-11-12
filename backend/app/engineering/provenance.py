"""Traceability contracts for engineering values.

This module validates metadata completeness. It does not validate the
scientific correctness or applicability of a source or equation.
"""
from datetime import datetime
from enum import StrEnum
from math import isfinite
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class ProvenanceClass(StrEnum):
    SOURCED = "sourced"
    CALCULATED = "calculated"
    ILLUSTRATIVE = "illustrative"


class CredibilityStatus(StrEnum):
    UNASSESSED = "unassessed"
    VERIFIED = "verified"
    VALIDATED = "validated"
    UNVALIDATED = "unvalidated"


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: Annotated[str, Field(min_length=1, max_length=120)]
    title: Annotated[str, Field(min_length=1, max_length=300)]
    url: HttpUrl | None = None
    version_or_release: Annotated[str, Field(min_length=1, max_length=120)]
    accessed_at: datetime | None = None


class EngineeringValue(BaseModel):
    """A numerical value with SI-oriented unit and explicit provenance."""

    model_config = ConfigDict(extra="forbid")

    value_id: Annotated[str, Field(min_length=1, max_length=120)]
    name: Annotated[str, Field(min_length=1, max_length=200)]
    value: float
    unit: Annotated[str, Field(min_length=1, max_length=40)]
    provenance: ProvenanceClass
    source: SourceReference | None = None
    equation_id: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    model_version: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    assumption_note: Annotated[str, Field(min_length=1, max_length=1000)] | None = None
    credibility: CredibilityStatus = CredibilityStatus.UNASSESSED
    intended_use: Annotated[str, Field(min_length=1, max_length=500)]
    limitations: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(default_factory=list)

    @field_validator("value")
    @classmethod
    def value_must_be_finite(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("Engineering values must be finite numbers")
        return value

    @model_validator(mode="after")
    def provenance_metadata_must_match(self) -> "EngineeringValue":
        if self.provenance == ProvenanceClass.SOURCED and self.source is None:
            raise ValueError("Sourced values require a source reference")
        if self.provenance == ProvenanceClass.CALCULATED:
            if not self.equation_id or not self.model_version:
                raise ValueError("Calculated values require equation_id and model_version")
        if self.provenance == ProvenanceClass.ILLUSTRATIVE and not self.assumption_note:
            raise ValueError("Illustrative values require an explicit assumption_note")
        if self.credibility == CredibilityStatus.VALIDATED:
            if not self.limitations:
                raise ValueError("Validated claims must document applicability limitations")
        return self
