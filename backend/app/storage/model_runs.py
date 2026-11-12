"""SQLite persistence for reproducible engineering model runs."""
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from app.storage.manifests import ManifestStore


class ModelRunSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    model_id: str
    model_version: str
    equation_id: str
    created_at: datetime
    result: dict[str, Any]


class ModelRunStore:
    """Append-only store for model inputs, outputs, assumptions and limitations."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        ManifestStore(self.database_path)

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

    def create(
        self,
        model_id: str,
        model_version: str,
        equation_id: str,
        result: dict[str, Any],
    ) -> ModelRunSnapshot:
        snapshot = ModelRunSnapshot(
            run_id=str(uuid4()),
            model_id=model_id,
            model_version=model_version,
            equation_id=equation_id,
            created_at=datetime.now(UTC),
            result=result,
        )
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO model_runs
                    (run_id, model_id, model_version, equation_id, created_at, payload_json, schema_version)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.run_id,
                    snapshot.model_id,
                    snapshot.model_version,
                    snapshot.equation_id,
                    snapshot.created_at.isoformat(),
                    snapshot.model_dump_json(),
                    ManifestStore.SCHEMA_VERSION,
                ),
            )
        return snapshot

    def get(self, run_id: str) -> ModelRunSnapshot | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM model_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return ModelRunSnapshot.model_validate_json(row["payload_json"])

    def list(self, limit: int = 50, offset: int = 0) -> list[ModelRunSnapshot]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM model_runs
                ORDER BY created_at DESC, run_id ASC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [ModelRunSnapshot.model_validate_json(row["payload_json"]) for row in rows]
