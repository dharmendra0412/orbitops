"""Append-only persistence for requirement verification evidence."""
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.missions.projects import MissionProjectDraft, VerificationMethod
from app.missions.verification import VerificationRecord, VerificationRecordCreate


class VerificationProjectNotFoundError(Exception):
    """The referenced mission project does not exist."""


class VerificationRequirementNotFoundError(Exception):
    """The requirement is not present in the latest project revision."""


class VerificationMethodMismatchError(Exception):
    """The evidence method conflicts with the requirement's planned method."""


class MissionVerificationStore:
    """Keep verification records append-only and tied to a project requirement."""

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
                CREATE TABLE IF NOT EXISTS mission_verification_records (
                    verification_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES mission_projects(project_id),
                    requirement_id TEXT NOT NULL,
                    method TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    performed_at TEXT NOT NULL,
                    performed_by TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    evidence_reference TEXT,
                    recorded_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_verification_project_time
                ON mission_verification_records(project_id, recorded_at DESC, verification_id)
                """
            )

    def create(
        self, project_id: UUID, payload: VerificationRecordCreate
    ) -> VerificationRecord:
        project_key = str(project_id)
        with self._connection() as connection:
            project = connection.execute(
                """
                SELECT r.payload_json
                FROM mission_projects p
                JOIN mission_project_revisions r
                  ON r.project_id = p.project_id
                 AND r.revision_number = p.latest_revision
                WHERE p.project_id = ?
                """,
                (project_key,),
            ).fetchone()
            if project is None:
                raise VerificationProjectNotFoundError(project_key)

            draft = MissionProjectDraft.model_validate_json(project["payload_json"])
            requirement = next(
                (item for item in draft.requirements if item.requirement_id == payload.requirement_id),
                None,
            )
            if requirement is None:
                raise VerificationRequirementNotFoundError(payload.requirement_id)
            if (
                requirement.verification_method != VerificationMethod.TBD
                and payload.method != requirement.verification_method
            ):
                raise VerificationMethodMismatchError(payload.requirement_id)

            verification_id = uuid4()
            recorded_at = datetime.now(UTC)
            record = VerificationRecord(
                **payload.model_dump(),
                verification_id=verification_id,
                project_id=project_id,
                recorded_at=recorded_at,
            )
            connection.execute(
                """
                INSERT INTO mission_verification_records
                    (verification_id, project_id, requirement_id, method, outcome,
                     performed_at, performed_by, summary, evidence_reference, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(record.verification_id),
                    project_key,
                    record.requirement_id,
                    record.method.value,
                    record.outcome.value,
                    record.performed_at.isoformat(),
                    record.performed_by,
                    record.summary,
                    record.evidence_reference,
                    record.recorded_at.isoformat(),
                ),
            )
        return record

    def list_for_project(self, project_id: UUID) -> list[VerificationRecord] | None:
        project_key = str(project_id)
        with self._connection() as connection:
            exists = connection.execute(
                "SELECT 1 FROM mission_projects WHERE project_id = ?", (project_key,)
            ).fetchone()
            if exists is None:
                return None
            rows = connection.execute(
                """
                SELECT * FROM mission_verification_records
                WHERE project_id = ?
                ORDER BY performed_at DESC, verification_id ASC
                """,
                (project_key,),
            ).fetchall()
        return [
            VerificationRecord(
                verification_id=UUID(row["verification_id"]),
                project_id=UUID(row["project_id"]),
                requirement_id=row["requirement_id"],
                method=VerificationMethod(row["method"]),
                outcome=row["outcome"],
                performed_at=datetime.fromisoformat(row["performed_at"]),
                performed_by=row["performed_by"],
                summary=row["summary"],
                evidence_reference=row["evidence_reference"],
                recorded_at=datetime.fromisoformat(row["recorded_at"]),
            )
            for row in rows
        ]
