"""SQLite persistence for immutable dataset manifests."""
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.manifests import DatasetManifest


class ManifestAlreadyExistsError(Exception):
    """Raised when a manifest identifier is already registered."""


class ManifestStore:
    """SQLite-backed registry for dataset metadata and model-run schema."""

    SCHEMA_VERSION = 2

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
            current_version = connection.execute("PRAGMA user_version").fetchone()[0]
            if current_version > self.SCHEMA_VERSION:
                raise RuntimeError("Database schema is newer than this ORBITOPS application")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dataset_manifests (
                    manifest_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    checksum_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    schema_version INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS model_runs (
                    run_id TEXT PRIMARY KEY,
                    model_id TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    equation_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    schema_version INTEGER NOT NULL
                )
                """
            )
            connection.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")

    def create(self, manifest: DatasetManifest) -> DatasetManifest:
        payload_json = json.dumps(
            manifest.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        created_at = datetime.now(UTC).isoformat()
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO dataset_manifests
                        (manifest_id, payload_json, checksum_sha256, created_at, schema_version)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        manifest.manifest_id,
                        payload_json,
                        manifest.checksum_sha256,
                        created_at,
                        self.SCHEMA_VERSION,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ManifestAlreadyExistsError(manifest.manifest_id) from error
        return manifest

    def get(self, manifest_id: str) -> DatasetManifest | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM dataset_manifests WHERE manifest_id = ?",
                (manifest_id,),
            ).fetchone()
        if row is None:
            return None
        return DatasetManifest.model_validate_json(row["payload_json"])

    def list(self, limit: int = 50, offset: int = 0) -> list[DatasetManifest]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM dataset_manifests
                ORDER BY created_at ASC, manifest_id ASC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [DatasetManifest.model_validate_json(row["payload_json"]) for row in rows]
