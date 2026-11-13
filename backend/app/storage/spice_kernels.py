"""Append-only SQLite registry for user-declared SPICE kernel metadata."""
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.storage.manifests import ManifestStore
from app.ephemeris.kernels import SpiceKernelRecord, SpiceKernelRegistration


class SpiceKernelAlreadyExistsError(Exception):
    """Raised when a kernel identifier has already been registered."""


class SpiceKernelStore:
    """Persists kernel metadata only; kernel binary files are never stored here."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        ManifestStore(self.database_path)
        with self._connection() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS spice_kernel_registrations (
                    kernel_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    registered_at TEXT NOT NULL
                )
            """)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create(self, registration: SpiceKernelRegistration) -> SpiceKernelRecord:
        record = SpiceKernelRecord(registration=registration, registered_at=datetime.now(UTC))
        payload = json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        try:
            with self._connection() as connection:
                connection.execute(
                    "INSERT INTO spice_kernel_registrations (kernel_id, payload_json, registered_at) VALUES (?, ?, ?)",
                    (registration.kernel_id, payload, record.registered_at.isoformat()),
                )
        except sqlite3.IntegrityError as error:
            raise SpiceKernelAlreadyExistsError(registration.kernel_id) from error
        return record

    def get(self, kernel_id: str) -> SpiceKernelRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM spice_kernel_registrations WHERE kernel_id = ?",
                (kernel_id,),
            ).fetchone()
        return SpiceKernelRecord.model_validate_json(row["payload_json"]) if row else None

    def list(self, limit: int = 50, offset: int = 0) -> list[SpiceKernelRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT payload_json FROM spice_kernel_registrations
                   ORDER BY registered_at ASC, kernel_id ASC LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [SpiceKernelRecord.model_validate_json(row["payload_json"]) for row in rows]
