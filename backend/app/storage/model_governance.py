"""Append-only model verification/validation evidence and derived credibility state."""
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.missions.model_governance import (
    ModelAssessment,
    ModelAssessmentCreate,
    ModelAssessmentKind,
    ModelAssessmentOutcome,
    ModelCredibilityState,
    ModelDefinition,
    ModelGovernanceCatalog,
)


MODEL_CATALOG = (
    {
        "model_id": "propulsion.ideal-rocket-equation",
        "display_name": "Ideal Tsiolkovsky rocket equation",
        "model_version": "0.1.0",
        "equation_ids": ["PROPULSION.IDEAL_ROCKET_EQUATION.V1"],
        "intended_scope": "Ideal delta-v exploration from dry mass, propellant mass, and specific impulse.",
    },
    {
        "model_id": "power.simple-energy-balance",
        "display_name": "Constant-power energy balance",
        "model_version": "0.1.0",
        "equation_ids": ["POWER.SIMPLE_ENERGY_BALANCE.V1"],
        "intended_scope": "Average supply/load energy bookkeeping over a fixed interval.",
    },
)


class ModelDefinitionNotFoundError(Exception):
    """Model ID, version, or equation is not in the application registry."""


class ModelAssessmentDatasetNotFoundError(Exception):
    """The referenced validation dataset manifest is not registered."""


class ModelGovernanceStore:
    """Store assessment evidence as immutable records; derive state from latest outcomes."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS model_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    model_id TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    equation_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    method TEXT NOT NULL,
                    performed_at TEXT NOT NULL,
                    performed_by TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    evidence_reference TEXT NOT NULL,
                    reference_dataset_id TEXT,
                    recorded_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_model_assessments_identity
                ON model_assessments(model_id, model_version, equation_id, kind, recorded_at DESC)
                """
            )

    @staticmethod
    def _definition(item: dict, assessments: list[ModelAssessment]) -> ModelDefinition:
        verification = [
            item for item in assessments if item.kind == ModelAssessmentKind.VERIFICATION
        ]
        validation = [
            item for item in assessments if item.kind == ModelAssessmentKind.VALIDATION
        ]
        latest_verification = max(verification, key=lambda item: item.recorded_at) if verification else None
        latest_validation = max(validation, key=lambda item: item.recorded_at) if validation else None

        if (
            (latest_verification and latest_verification.outcome != ModelAssessmentOutcome.PASS)
            or (latest_validation and latest_validation.outcome != ModelAssessmentOutcome.PASS)
        ):
            state = ModelCredibilityState.REVIEW_REQUIRED
        elif latest_verification and latest_validation:
            state = ModelCredibilityState.VALIDATED
        elif latest_verification:
            state = ModelCredibilityState.VERIFIED
        else:
            state = ModelCredibilityState.UNVALIDATED

        return ModelDefinition(
            **item,
            current_state=state,
            latest_verification_outcome=(
                latest_verification.outcome if latest_verification else None
            ),
            latest_validation_outcome=latest_validation.outcome if latest_validation else None,
            assessment_count=len(assessments),
        )

    @staticmethod
    def _assessment(row: sqlite3.Row) -> ModelAssessment:
        return ModelAssessment(
            assessment_id=UUID(row["assessment_id"]),
            model_id=row["model_id"],
            model_version=row["model_version"],
            equation_id=row["equation_id"],
            kind=ModelAssessmentKind(row["kind"]),
            outcome=ModelAssessmentOutcome(row["outcome"]),
            method=row["method"],
            performed_at=datetime.fromisoformat(row["performed_at"]),
            performed_by=row["performed_by"],
            summary=row["summary"],
            evidence_reference=row["evidence_reference"],
            reference_dataset_id=row["reference_dataset_id"],
            recorded_at=datetime.fromisoformat(row["recorded_at"]),
        )

    def create(self, payload: ModelAssessmentCreate) -> ModelAssessment:
        definition = next(
            (
                item for item in MODEL_CATALOG
                if item["model_id"] == payload.model_id
                and item["model_version"] == payload.model_version
                and payload.equation_id in item["equation_ids"]
            ),
            None,
        )
        if definition is None:
            raise ModelDefinitionNotFoundError(payload.model_id)

        with self._connection() as connection:
            if payload.reference_dataset_id is not None:
                manifest_table = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'dataset_manifests'"
                ).fetchone()
                if manifest_table is None:
                    raise ModelAssessmentDatasetNotFoundError(payload.reference_dataset_id)
                dataset = connection.execute(
                    "SELECT 1 FROM dataset_manifests WHERE manifest_id = ?",
                    (payload.reference_dataset_id,),
                ).fetchone()
                if dataset is None:
                    raise ModelAssessmentDatasetNotFoundError(payload.reference_dataset_id)

            record = ModelAssessment(
                **payload.model_dump(),
                assessment_id=uuid4(),
                recorded_at=datetime.now(UTC),
            )
            connection.execute(
                """
                INSERT INTO model_assessments
                    (assessment_id, model_id, model_version, equation_id, kind, outcome,
                     method, performed_at, performed_by, summary, evidence_reference,
                     reference_dataset_id, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(record.assessment_id), record.model_id, record.model_version,
                    record.equation_id, record.kind.value, record.outcome.value,
                    record.method.value, record.performed_at.isoformat(), record.performed_by,
                    record.summary, record.evidence_reference, record.reference_dataset_id,
                    record.recorded_at.isoformat(),
                ),
            )
        return record

    def list_assessments(
        self, model_id: str | None = None, model_version: str | None = None
    ) -> list[ModelAssessment]:
        query = "SELECT * FROM model_assessments"
        clauses = []
        params: list[str] = []
        if model_id is not None:
            clauses.append("model_id = ?")
            params.append(model_id)
        if model_version is not None:
            clauses.append("model_version = ?")
            params.append(model_version)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY recorded_at DESC, assessment_id ASC"
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._assessment(row) for row in rows]

    def catalog(self) -> ModelGovernanceCatalog:
        assessments = self.list_assessments()
        definitions = [
            self._definition(
                item,
                [
                    record for record in assessments
                    if record.model_id == item["model_id"]
                    and record.model_version == item["model_version"]
                    and record.equation_id in item["equation_ids"]
                ],
            )
            for item in MODEL_CATALOG
        ]
        return ModelGovernanceCatalog(
            models=definitions,
            limitations=[
                "Model credibility state is derived from recorded assessment outcomes, not an independent audit.",
                "A verification pass records evidence of implementation checks; it does not establish scientific validity.",
                "A validation pass records evidence of comparison with reference observations/data; applicability still requires expert review.",
                "A validated state is not flight qualification, safety approval, operational authorization, or certification.",
                "Evidence references are user-supplied strings and are not fetched or authenticated.",
                "Only the model IDs, versions, and equation IDs listed in this application registry can be assessed.",
            ],
        )
