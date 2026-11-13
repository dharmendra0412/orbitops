"""Append-only SQLite registry for user-declared SPICE kernel metadata."""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.ephemeris.kernels import (
    SpiceKernelArtifactRecord,
    SpiceKernelInspectionRecord,
    SpiceKernelRecord,
    SpiceKernelRegistration,
    SpiceFrameTransformRecord,
    SpiceTimeConversionRecord,
)
from app.storage.manifests import ManifestStore


class SpiceKernelAlreadyExistsError(Exception):
    """Raised when a kernel identifier or artifact has already been registered."""


class SpiceKernelStore:
    """Persists kernel provenance and artifact metadata, not binary file contents."""

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
            connection.execute("""
                CREATE TABLE IF NOT EXISTS spice_kernel_artifacts (
                    kernel_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    FOREIGN KEY(kernel_id) REFERENCES spice_kernel_registrations(kernel_id)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS spice_time_conversions (
                    conversion_id TEXT PRIMARY KEY,
                    kernel_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    converted_at TEXT NOT NULL,
                    FOREIGN KEY(kernel_id) REFERENCES spice_kernel_inspections(kernel_id)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS spice_kernel_inspections (
                    kernel_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    inspected_at TEXT NOT NULL,
                    FOREIGN KEY(kernel_id) REFERENCES spice_kernel_artifacts(kernel_id)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS spice_frame_transformations (
                    transformation_id TEXT PRIMARY KEY,
                    kernel_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    transformed_at TEXT NOT NULL,
                    FOREIGN KEY(kernel_id) REFERENCES spice_kernel_inspections(kernel_id)
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

    def create_artifact(self, artifact: SpiceKernelArtifactRecord) -> SpiceKernelArtifactRecord:
        payload = json.dumps(artifact.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        try:
            with self._connection() as connection:
                connection.execute(
                    "INSERT INTO spice_kernel_artifacts (kernel_id, payload_json, acquired_at) VALUES (?, ?, ?)",
                    (artifact.kernel_id, payload, artifact.acquired_at.isoformat()),
                )
        except sqlite3.IntegrityError as error:
            raise SpiceKernelAlreadyExistsError(artifact.kernel_id) from error
        return artifact

    def get_artifact(self, kernel_id: str) -> SpiceKernelArtifactRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM spice_kernel_artifacts WHERE kernel_id = ?",
                (kernel_id,),
            ).fetchone()
        return SpiceKernelArtifactRecord.model_validate_json(row["payload_json"]) if row else None


    def create_inspection(self, inspection: SpiceKernelInspectionRecord) -> SpiceKernelInspectionRecord:
        payload = json.dumps(
            inspection.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        try:
            with self._connection() as connection:
                connection.execute(
                    "INSERT INTO spice_kernel_inspections (kernel_id, payload_json, inspected_at) VALUES (?, ?, ?)",
                    (inspection.kernel_id, payload, inspection.inspected_at.isoformat()),
                )
        except sqlite3.IntegrityError as error:
            raise SpiceKernelAlreadyExistsError(inspection.kernel_id) from error
        return inspection

    def get_inspection(self, kernel_id: str) -> SpiceKernelInspectionRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM spice_kernel_inspections WHERE kernel_id = ?",
                (kernel_id,),
            ).fetchone()
        return SpiceKernelInspectionRecord.model_validate_json(row["payload_json"]) if row else None

    def create_time_conversion(
        self, conversion: SpiceTimeConversionRecord
    ) -> SpiceTimeConversionRecord:
        payload = json.dumps(
            conversion.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO spice_time_conversions
                   (conversion_id, kernel_id, payload_json, converted_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    conversion.conversion_id,
                    conversion.kernel_id,
                    payload,
                    conversion.converted_at.isoformat(),
                ),
            )
        return conversion

    def get_time_conversion(self, conversion_id: str) -> SpiceTimeConversionRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM spice_time_conversions WHERE conversion_id = ?",
                (conversion_id,),
            ).fetchone()
        return SpiceTimeConversionRecord.model_validate_json(row["payload_json"]) if row else None

    def list_time_conversions(
        self, kernel_id: str, limit: int = 50, offset: int = 0
    ) -> list[SpiceTimeConversionRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT payload_json FROM spice_time_conversions
                   WHERE kernel_id = ? ORDER BY converted_at DESC, conversion_id ASC
                   LIMIT ? OFFSET ?""",
                (kernel_id, limit, offset),
            ).fetchall()
        return [SpiceTimeConversionRecord.model_validate_json(row["payload_json"]) for row in rows]


    def create_frame_transformation(
        self, transformation: SpiceFrameTransformRecord
    ) -> SpiceFrameTransformRecord:
        payload = json.dumps(
            transformation.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO spice_frame_transformations
                   (transformation_id, kernel_id, payload_json, transformed_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    transformation.transformation_id,
                    transformation.kernel_id,
                    payload,
                    transformation.transformed_at.isoformat(),
                ),
            )
        return transformation

    def get_frame_transformation(
        self, transformation_id: str
    ) -> SpiceFrameTransformRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM spice_frame_transformations WHERE transformation_id = ?",
                (transformation_id,),
            ).fetchone()
        return SpiceFrameTransformRecord.model_validate_json(row["payload_json"]) if row else None

    def list_frame_transformations(
        self, kernel_id: str, limit: int = 50, offset: int = 0
    ) -> list[SpiceFrameTransformRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT payload_json FROM spice_frame_transformations
                   WHERE kernel_id = ? ORDER BY transformed_at DESC, transformation_id ASC
                   LIMIT ? OFFSET ?""",
                (kernel_id, limit, offset),
            ).fetchall()
        return [SpiceFrameTransformRecord.model_validate_json(row["payload_json"]) for row in rows]
