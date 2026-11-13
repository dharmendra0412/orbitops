"""SQLite persistence for mission workspaces and immutable revisions."""
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.missions.projects import (
    MissionProjectDraft,
    MissionProjectRecord,
    MissionProjectRevision,
    MissionProjectSummary,
)


class MissionProjectNotFoundError(Exception):
    """Raised when a mission project does not exist."""


class MissionProjectStore:
    """Persist mission metadata and append-only, reproducible draft revisions."""

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
                CREATE TABLE IF NOT EXISTS mission_projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    target_body TEXT NOT NULL,
                    mission_archetype TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    latest_revision INTEGER NOT NULL CHECK (latest_revision >= 1)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mission_project_revisions (
                    revision_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES mission_projects(project_id),
                    revision_number INTEGER NOT NULL CHECK (revision_number >= 1),
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE(project_id, revision_number)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mission_projects_updated
                ON mission_projects(updated_at DESC, project_id ASC)
                """
            )

    @staticmethod
    def _revision(row: sqlite3.Row) -> MissionProjectRevision:
        payload: dict[str, Any] = json.loads(row["payload_json"])
        return MissionProjectRevision(
            revision_id=UUID(row["revision_id"]),
            project_id=UUID(row["project_id"]),
            revision_number=row["revision_number"],
            created_at=datetime.fromisoformat(row["created_at"]),
            draft=MissionProjectDraft.model_validate(payload),
        )

    def _record(self, connection: sqlite3.Connection, project_id: str) -> MissionProjectRecord | None:
        project = connection.execute(
            "SELECT * FROM mission_projects WHERE project_id = ?", (project_id,)
        ).fetchone()
        if project is None:
            return None
        revision = connection.execute(
            """
            SELECT * FROM mission_project_revisions
            WHERE project_id = ? AND revision_number = ?
            """,
            (project_id, project["latest_revision"]),
        ).fetchone()
        if revision is None:
            raise RuntimeError("Mission project has no corresponding latest revision")
        return MissionProjectRecord(
            project_id=UUID(project["project_id"]),
            name=project["name"],
            target_body=project["target_body"],
            mission_archetype=project["mission_archetype"],
            created_at=datetime.fromisoformat(project["created_at"]),
            updated_at=datetime.fromisoformat(project["updated_at"]),
            latest_revision=project["latest_revision"],
            revision=self._revision(revision),
        )

    def create(self, draft: MissionProjectDraft) -> MissionProjectRecord:
        project_id = str(uuid4())
        revision_id = str(uuid4())
        now = datetime.now(UTC)
        payload_json = json.dumps(
            draft.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO mission_projects
                    (project_id, name, target_body, mission_archetype, created_at, updated_at, latest_revision)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    project_id, draft.name, draft.target_body, draft.mission_archetype,
                    now.isoformat(), now.isoformat(),
                ),
            )
            connection.execute(
                """
                INSERT INTO mission_project_revisions
                    (revision_id, project_id, revision_number, created_at, payload_json)
                VALUES (?, ?, 1, ?, ?)
                """,
                (revision_id, project_id, now.isoformat(), payload_json),
            )
            record = self._record(connection, project_id)
        if record is None:
            raise RuntimeError("Created mission project could not be retrieved")
        return record

    def create_revision(self, project_id: UUID, draft: MissionProjectDraft) -> MissionProjectRecord:
        project_key = str(project_id)
        revision_id = str(uuid4())
        now = datetime.now(UTC)
        payload_json = json.dumps(
            draft.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        with self._connection() as connection:
            # Reserve the SQLite write lock before reading the current revision.
            # This makes the read/increment/insert/update sequence atomic across
            # concurrent requests and prevents two writers choosing the same number.
            connection.execute("BEGIN IMMEDIATE")
            project = connection.execute(
                "SELECT latest_revision FROM mission_projects WHERE project_id = ?",
                (project_key,),
            ).fetchone()
            if project is None:
                raise MissionProjectNotFoundError(project_key)
            next_revision = project["latest_revision"] + 1
            connection.execute(
                """
                INSERT INTO mission_project_revisions
                    (revision_id, project_id, revision_number, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (revision_id, project_key, next_revision, now.isoformat(), payload_json),
            )
            connection.execute(
                """
                UPDATE mission_projects
                SET name = ?, target_body = ?, mission_archetype = ?,
                    updated_at = ?, latest_revision = ?
                WHERE project_id = ?
                """,
                (
                    draft.name, draft.target_body, draft.mission_archetype,
                    now.isoformat(), next_revision, project_key,
                ),
            )
            record = self._record(connection, project_key)
        if record is None:
            raise RuntimeError("Revised mission project could not be retrieved")
        return record

    def get(self, project_id: UUID) -> MissionProjectRecord | None:
        with self._connection() as connection:
            return self._record(connection, str(project_id))

    def list(self, limit: int = 50, offset: int = 0) -> list[MissionProjectSummary]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT project_id, name, target_body, mission_archetype,
                       created_at, updated_at, latest_revision
                FROM mission_projects
                ORDER BY updated_at DESC, project_id ASC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [
            MissionProjectSummary(
                project_id=UUID(row["project_id"]),
                name=row["name"],
                target_body=row["target_body"],
                mission_archetype=row["mission_archetype"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                latest_revision=row["latest_revision"],
            )
            for row in rows
        ]
