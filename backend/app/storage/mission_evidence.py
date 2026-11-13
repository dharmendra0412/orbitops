"""Append-only associations between mission projects and reusable evidence records."""
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.ingestion.manifests import DatasetManifest
from app.missions.project_evidence import (
    MissionDatasetLink,
    MissionDatasetLinkCreate,
    MissionModelAssessmentLink,
    MissionModelAssessmentLinkCreate,
)
from app.storage.model_governance import ModelGovernanceStore


class MissionEvidenceProjectNotFoundError(Exception):
    """Mission project does not exist."""


class MissionEvidenceDatasetNotFoundError(Exception):
    """Dataset manifest does not exist."""


class MissionEvidenceAssessmentNotFoundError(Exception):
    """Model assessment does not exist."""


class MissionEvidenceLinkExistsError(Exception):
    """The evidence item is already linked to this mission project."""


class MissionEvidenceStore:
    """Link immutable external evidence records to a project without copying artifacts."""

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
                CREATE TABLE IF NOT EXISTS mission_dataset_links (
                    link_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES mission_projects(project_id),
                    manifest_id TEXT NOT NULL REFERENCES dataset_manifests(manifest_id),
                    purpose TEXT NOT NULL,
                    linked_by TEXT NOT NULL,
                    linked_at TEXT NOT NULL,
                    UNIQUE(project_id, manifest_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mission_model_assessment_links (
                    link_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES mission_projects(project_id),
                    assessment_id TEXT NOT NULL REFERENCES model_assessments(assessment_id),
                    rationale TEXT NOT NULL,
                    linked_by TEXT NOT NULL,
                    linked_at TEXT NOT NULL,
                    UNIQUE(project_id, assessment_id)
                )
                """
            )

    @staticmethod
    def _project_exists(connection: sqlite3.Connection, project_id: UUID) -> bool:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'mission_projects'"
        ).fetchone()
        if table is None:
            return False
        return connection.execute(
            "SELECT 1 FROM mission_projects WHERE project_id = ?", (str(project_id),)
        ).fetchone() is not None

    def create_dataset_link(
        self, project_id: UUID, payload: MissionDatasetLinkCreate
    ) -> MissionDatasetLink:
        with self._connection() as connection:
            if not self._project_exists(connection, project_id):
                raise MissionEvidenceProjectNotFoundError(str(project_id))
            manifest_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'dataset_manifests'"
            ).fetchone()
            if manifest_table is None:
                raise MissionEvidenceDatasetNotFoundError(payload.manifest_id)
            manifest_row = connection.execute(
                "SELECT payload_json FROM dataset_manifests WHERE manifest_id = ?",
                (payload.manifest_id,),
            ).fetchone()
            if manifest_row is None:
                raise MissionEvidenceDatasetNotFoundError(payload.manifest_id)

            link_id = uuid4()
            linked_at = datetime.now(UTC)
            try:
                connection.execute(
                    """
                    INSERT INTO mission_dataset_links
                        (link_id, project_id, manifest_id, purpose, linked_by, linked_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(link_id), str(project_id), payload.manifest_id,
                        payload.purpose, payload.linked_by, linked_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                if "UNIQUE constraint failed" in str(error):
                    raise MissionEvidenceLinkExistsError(payload.manifest_id) from error
                raise

        return MissionDatasetLink(
            link_id=link_id,
            project_id=project_id,
            manifest=DatasetManifest.model_validate_json(manifest_row["payload_json"]),
            purpose=payload.purpose,
            linked_by=payload.linked_by,
            linked_at=linked_at,
        )

    def list_dataset_links(self, project_id: UUID) -> list[MissionDatasetLink] | None:
        with self._connection() as connection:
            if not self._project_exists(connection, project_id):
                return None
            manifest_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'dataset_manifests'"
            ).fetchone()
            if manifest_table is None:
                return []
            rows = connection.execute(
                """
                SELECT l.*, m.payload_json
                FROM mission_dataset_links l
                JOIN dataset_manifests m ON m.manifest_id = l.manifest_id
                WHERE l.project_id = ?
                ORDER BY l.linked_at, l.link_id
                """,
                (str(project_id),),
            ).fetchall()
        return [
            MissionDatasetLink(
                link_id=UUID(row["link_id"]),
                project_id=UUID(row["project_id"]),
                manifest=DatasetManifest.model_validate_json(row["payload_json"]),
                purpose=row["purpose"],
                linked_by=row["linked_by"],
                linked_at=datetime.fromisoformat(row["linked_at"]),
            )
            for row in rows
        ]

    def create_model_assessment_link(
        self, project_id: UUID, payload: MissionModelAssessmentLinkCreate
    ) -> MissionModelAssessmentLink:
        with self._connection() as connection:
            if not self._project_exists(connection, project_id):
                raise MissionEvidenceProjectNotFoundError(str(project_id))
            assessment_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'model_assessments'"
            ).fetchone()
            if assessment_table is None:
                raise MissionEvidenceAssessmentNotFoundError(str(payload.assessment_id))
            assessment_row = connection.execute(
                "SELECT * FROM model_assessments WHERE assessment_id = ?",
                (str(payload.assessment_id),),
            ).fetchone()
            if assessment_row is None:
                raise MissionEvidenceAssessmentNotFoundError(str(payload.assessment_id))

            link_id = uuid4()
            linked_at = datetime.now(UTC)
            try:
                connection.execute(
                    """
                    INSERT INTO mission_model_assessment_links
                        (link_id, project_id, assessment_id, rationale, linked_by, linked_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(link_id), str(project_id), str(payload.assessment_id),
                        payload.rationale, payload.linked_by, linked_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                if "UNIQUE constraint failed" in str(error):
                    raise MissionEvidenceLinkExistsError(str(payload.assessment_id)) from error
                raise

        return MissionModelAssessmentLink(
            link_id=link_id,
            project_id=project_id,
            assessment=ModelGovernanceStore._assessment(assessment_row),
            rationale=payload.rationale,
            linked_by=payload.linked_by,
            linked_at=linked_at,
        )

    def list_model_assessment_links(
        self, project_id: UUID
    ) -> list[MissionModelAssessmentLink] | None:
        with self._connection() as connection:
            if not self._project_exists(connection, project_id):
                return None
            assessment_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'model_assessments'"
            ).fetchone()
            if assessment_table is None:
                return []
            rows = connection.execute(
                """
                SELECT l.*, a.*
                FROM mission_model_assessment_links l
                JOIN model_assessments a ON a.assessment_id = l.assessment_id
                WHERE l.project_id = ?
                ORDER BY l.linked_at, l.link_id
                """,
                (str(project_id),),
            ).fetchall()
        results = []
        for row in rows:
            results.append(
                MissionModelAssessmentLink(
                    link_id=UUID(row["link_id"]),
                    project_id=UUID(row["project_id"]),
                    assessment=ModelGovernanceStore._assessment(row),
                    rationale=row["rationale"],
                    linked_by=row["linked_by"],
                    linked_at=datetime.fromisoformat(row["linked_at"]),
                )
            )
        return results
