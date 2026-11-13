"""SQLite persistence for spacecraft configuration snapshots."""
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.missions.spacecraft import (
    SpacecraftConfigurationDraft,
    SpacecraftConfigurationRecord,
    SpacecraftConfigurationRevision,
)


class SpacecraftProjectNotFoundError(Exception):
    """The mission project does not exist."""


class SpacecraftConfigurationNotFoundError(Exception):
    """The mission project has no spacecraft configuration."""


class SpacecraftConfigurationExistsError(Exception):
    """The mission project already has a spacecraft configuration."""


class SpacecraftConfigurationStore:
    """Persist configuration revisions as immutable project-linked snapshots."""

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
                CREATE TABLE IF NOT EXISTS spacecraft_configurations (
                    configuration_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL UNIQUE REFERENCES mission_projects(project_id),
                    latest_revision INTEGER NOT NULL CHECK (latest_revision >= 1)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS spacecraft_configuration_revisions (
                    revision_id TEXT PRIMARY KEY,
                    configuration_id TEXT NOT NULL REFERENCES spacecraft_configurations(configuration_id),
                    revision_number INTEGER NOT NULL CHECK (revision_number >= 1),
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE(configuration_id, revision_number)
                )
                """
            )

    @staticmethod
    def _record(
        connection: sqlite3.Connection, configuration: sqlite3.Row
    ) -> SpacecraftConfigurationRecord:
        revision = connection.execute(
            """
            SELECT * FROM spacecraft_configuration_revisions
            WHERE configuration_id = ? AND revision_number = ?
            """,
            (configuration["configuration_id"], configuration["latest_revision"]),
        ).fetchone()
        if revision is None:
            raise RuntimeError("Spacecraft configuration has no latest revision")
        return SpacecraftConfigurationRecord(
            configuration_id=UUID(configuration["configuration_id"]),
            project_id=UUID(configuration["project_id"]),
            latest_revision=configuration["latest_revision"],
            revision=SpacecraftConfigurationRevision(
                revision_id=UUID(revision["revision_id"]),
                project_id=UUID(configuration["project_id"]),
                revision_number=revision["revision_number"],
                created_at=revision["created_at"],
                draft=SpacecraftConfigurationDraft.model_validate_json(revision["payload_json"]),
            ),
        )

    def create(
        self, project_id: UUID, draft: SpacecraftConfigurationDraft
    ) -> SpacecraftConfigurationRecord:
        with self._connection() as connection:
            project = connection.execute(
                "SELECT 1 FROM mission_projects WHERE project_id = ?", (str(project_id),)
            ).fetchone()
            if project is None:
                raise SpacecraftProjectNotFoundError(str(project_id))
            existing = connection.execute(
                "SELECT 1 FROM spacecraft_configurations WHERE project_id = ?", (str(project_id),)
            ).fetchone()
            if existing is not None:
                raise SpacecraftConfigurationExistsError(str(project_id))
            configuration_id = str(uuid4())
            now = datetime.now(UTC).isoformat()
            connection.execute(
                "INSERT INTO spacecraft_configurations VALUES (?, ?, 1)",
                (configuration_id, str(project_id)),
            )
            connection.execute(
                """
                INSERT INTO spacecraft_configuration_revisions
                    (revision_id, configuration_id, revision_number, created_at, payload_json)
                VALUES (?, ?, 1, ?, ?)
                """,
                (
                    str(uuid4()), configuration_id, now,
                    json.dumps(draft.model_dump(mode="json"), sort_keys=True),
                ),
            )
            row = connection.execute(
                "SELECT * FROM spacecraft_configurations WHERE configuration_id = ?",
                (configuration_id,),
            ).fetchone()
            return self._record(connection, row)

    def create_revision(
        self, project_id: UUID, draft: SpacecraftConfigurationDraft
    ) -> SpacecraftConfigurationRecord:
        with self._connection() as connection:
            configuration = connection.execute(
                "SELECT * FROM spacecraft_configurations WHERE project_id = ?", (str(project_id),)
            ).fetchone()
            if configuration is None:
                project = connection.execute(
                    "SELECT 1 FROM mission_projects WHERE project_id = ?", (str(project_id),)
                ).fetchone()
                if project is None:
                    raise SpacecraftProjectNotFoundError(str(project_id))
                raise SpacecraftConfigurationNotFoundError(str(project_id))
            revision_number = configuration["latest_revision"] + 1
            now = datetime.now(UTC).isoformat()
            connection.execute(
                """
                INSERT INTO spacecraft_configuration_revisions
                    (revision_id, configuration_id, revision_number, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()), configuration["configuration_id"], revision_number, now,
                    json.dumps(draft.model_dump(mode="json"), sort_keys=True),
                ),
            )
            connection.execute(
                "UPDATE spacecraft_configurations SET latest_revision = ? WHERE configuration_id = ?",
                (revision_number, configuration["configuration_id"]),
            )
            updated = connection.execute(
                "SELECT * FROM spacecraft_configurations WHERE configuration_id = ?",
                (configuration["configuration_id"],),
            ).fetchone()
            return self._record(connection, updated)

    def get(self, project_id: UUID) -> SpacecraftConfigurationRecord | None:
        with self._connection() as connection:
            configuration = connection.execute(
                "SELECT * FROM spacecraft_configurations WHERE project_id = ?", (str(project_id),)
            ).fetchone()
            return None if configuration is None else self._record(connection, configuration)
