"""Append-only requirement-to-spacecraft allocation persistence."""
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.missions.projects import MissionProjectDraft
from app.missions.traceability import (
    RequirementAllocation,
    RequirementAllocationCreate,
    RequirementTraceabilityMatrix,
    RequirementTraceabilityRow,
)
from app.missions.verification import VerificationOutcome


class TraceabilityProjectNotFoundError(Exception):
    """Mission project does not exist."""


class TraceabilityRequirementNotFoundError(Exception):
    """Requirement does not exist in the latest mission revision."""


class TraceabilityConfigurationNotFoundError(Exception):
    """Spacecraft configuration does not exist."""


class TraceabilityComponentNotFoundError(Exception):
    """Component does not exist in the latest spacecraft configuration."""


class TraceabilityAllocationExistsError(Exception):
    """The requirement is already allocated to this component."""


class RequirementTraceabilityStore:
    """Keep allocation events append-only and build a latest-revision matrix."""

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
                CREATE TABLE IF NOT EXISTS requirement_allocations (
                    allocation_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES mission_projects(project_id),
                    requirement_id TEXT NOT NULL,
                    component_id TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    allocated_by TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(project_id, requirement_id, component_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_requirement_allocations_project
                ON requirement_allocations(project_id, requirement_id, recorded_at)
                """
            )

    @staticmethod
    def _allocation(row: sqlite3.Row) -> RequirementAllocation:
        return RequirementAllocation(
            allocation_id=UUID(row["allocation_id"]),
            project_id=UUID(row["project_id"]),
            requirement_id=row["requirement_id"],
            component_id=row["component_id"],
            rationale=row["rationale"],
            allocated_by=row["allocated_by"],
            recorded_at=datetime.fromisoformat(row["recorded_at"]),
        )

    def create(
        self, project_id: UUID, payload: RequirementAllocationCreate
    ) -> RequirementAllocation:
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
                raise TraceabilityProjectNotFoundError(project_key)
            draft = MissionProjectDraft.model_validate_json(project["payload_json"])
            if not any(item.requirement_id == payload.requirement_id for item in draft.requirements):
                raise TraceabilityRequirementNotFoundError(payload.requirement_id)

            configuration = connection.execute(
                """
                SELECT c.configuration_id, c.latest_revision, r.payload_json
                FROM spacecraft_configurations c
                JOIN spacecraft_configuration_revisions r
                  ON r.configuration_id = c.configuration_id
                 AND r.revision_number = c.latest_revision
                WHERE c.project_id = ?
                """,
                (project_key,),
            ).fetchone()
            if configuration is None:
                raise TraceabilityConfigurationNotFoundError(project_key)
            component_ids = {
                component["component_id"]
                for component in __import__("json").loads(configuration["payload_json"])["components"]
            }
            if payload.component_id not in component_ids:
                raise TraceabilityComponentNotFoundError(payload.component_id)

            allocation_id = uuid4()
            recorded_at = datetime.now(UTC)
            try:
                connection.execute(
                    """
                    INSERT INTO requirement_allocations
                        (allocation_id, project_id, requirement_id, component_id,
                         rationale, allocated_by, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(allocation_id), project_key, payload.requirement_id,
                        payload.component_id, payload.rationale, payload.allocated_by,
                        recorded_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                if "UNIQUE constraint failed" in str(error):
                    raise TraceabilityAllocationExistsError(payload.component_id) from error
                raise
        return RequirementAllocation(
            allocation_id=allocation_id,
            project_id=project_id,
            **payload.model_dump(),
            recorded_at=recorded_at,
        )

    def matrix(self, project_id: UUID) -> RequirementTraceabilityMatrix | None:
        project_key = str(project_id)
        with self._connection() as connection:
            project = connection.execute(
                """
                SELECT p.latest_revision, r.payload_json
                FROM mission_projects p
                JOIN mission_project_revisions r
                  ON r.project_id = p.project_id
                 AND r.revision_number = p.latest_revision
                WHERE p.project_id = ?
                """,
                (project_key,),
            ).fetchone()
            if project is None:
                return None

            configuration = connection.execute(
                """
                SELECT c.latest_revision, r.payload_json
                FROM spacecraft_configurations c
                JOIN spacecraft_configuration_revisions r
                  ON r.configuration_id = c.configuration_id
                 AND r.revision_number = c.latest_revision
                WHERE c.project_id = ?
                """,
                (project_key,),
            ).fetchone()
            current_components = set()
            configuration_revision = None
            if configuration is not None:
                import json
                current_components = {
                    component["component_id"]
                    for component in json.loads(configuration["payload_json"])["components"]
                }
                configuration_revision = configuration["latest_revision"]

            import json
            mission_draft = MissionProjectDraft.model_validate_json(project["payload_json"])
            allocation_rows = connection.execute(
                """
                SELECT * FROM requirement_allocations
                WHERE project_id = ?
                ORDER BY requirement_id, component_id, recorded_at, allocation_id
                """,
                (project_key,),
            ).fetchall()
            evidence_rows = connection.execute(
                """
                SELECT requirement_id, outcome, COUNT(*) AS record_count
                FROM mission_verification_records
                WHERE project_id = ?
                GROUP BY requirement_id, outcome
                """,
                (project_key,),
            ).fetchall()

        allocations_by_requirement: dict[str, list[RequirementAllocation]] = {}
        for row in allocation_rows:
            allocation = self._allocation(row)
            allocations_by_requirement.setdefault(allocation.requirement_id, []).append(allocation)

        evidence_by_requirement: dict[str, dict[str, int]] = {}
        for row in evidence_rows:
            evidence_by_requirement.setdefault(row["requirement_id"], {})[row["outcome"]] = row["record_count"]

        rows = []
        for requirement in mission_draft.requirements:
            allocations = allocations_by_requirement.get(requirement.requirement_id, [])
            stale_ids = sorted(
                {item.component_id for item in allocations if item.component_id not in current_components}
            )
            evidence = evidence_by_requirement.get(requirement.requirement_id, {})
            total_evidence = sum(evidence.values())
            rows.append(
                RequirementTraceabilityRow(
                    requirement_id=requirement.requirement_id,
                    requirement_title=requirement.title,
                    requirement_statement=requirement.statement,
                    requirement_category=requirement.category.value,
                    verification_method=requirement.verification_method.value,
                    allocated=bool(allocations),
                    allocation_count=len(allocations),
                    allocations=allocations,
                    active_component_count=len(
                        {item.component_id for item in allocations if item.component_id in current_components}
                    ),
                    stale_component_ids=stale_ids,
                    verification_record_count=total_evidence,
                    pass_record_count=evidence.get(VerificationOutcome.PASS.value, 0),
                    fail_record_count=evidence.get(VerificationOutcome.FAIL.value, 0),
                    inconclusive_record_count=evidence.get(VerificationOutcome.INCONCLUSIVE.value, 0),
                    verification_evidence_present=total_evidence > 0,
                )
            )

        allocated_count = sum(row.allocated for row in rows)
        return RequirementTraceabilityMatrix(
            project_id=project_id,
            mission_revision=project["latest_revision"],
            spacecraft_configuration_revision=configuration_revision,
            requirement_count=len(rows),
            allocated_requirement_count=allocated_count,
            unallocated_requirement_count=len(rows) - allocated_count,
            rows=rows,
            limitations=[
                "Allocation records express traceability intent; they do not prove a component satisfies a requirement.",
                "Verification records are evidence entries only; a pass outcome is not independent acceptance or formal closure.",
                "Allocations referencing components absent from the latest configuration are flagged as stale and require review.",
                "The matrix uses the latest mission and spacecraft revisions; historical revision comparisons are not provided.",
                "Authentication, authorization, and independent engineering approval are not implemented.",
            ],
        )
