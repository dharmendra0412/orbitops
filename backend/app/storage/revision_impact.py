"""Compare immutable mission and spacecraft revisions for change-impact review."""
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from app.missions.revision_impact import (
    AllocationImpact,
    ComponentRevisionChange,
    RequirementRevisionChange,
    RevisionChangeImpactReport,
    RevisionChangeType,
)


class RevisionImpactProjectNotFoundError(Exception):
    """Mission project does not exist."""


class RevisionImpactRevisionNotFoundError(Exception):
    """One or more requested revisions do not exist."""


class RevisionImpactConfigurationNotFoundError(Exception):
    """Spacecraft configuration does not exist for this mission project."""


class RevisionImpactRangeError(Exception):
    """The target revision must not precede the baseline revision."""


class RevisionImpactStore:
    """Read-only historical comparison over immutable project/configuration snapshots."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

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

    @staticmethod
    def _diff_records(
        baseline: dict[str, dict],
        target: dict[str, dict],
    ) -> list[dict]:
        changes = []
        for record_id in sorted(set(baseline) | set(target)):
            old = baseline.get(record_id)
            new = target.get(record_id)
            if old is None and new is not None:
                changes.append({"id": record_id, "type": RevisionChangeType.ADDED, "old": None, "new": new, "fields": []})
            elif old is not None and new is None:
                changes.append({"id": record_id, "type": RevisionChangeType.REMOVED, "old": old, "new": None, "fields": []})
            elif old != new:
                fields = sorted(field for field in set(old) | set(new) if old.get(field) != new.get(field))
                changes.append({"id": record_id, "type": RevisionChangeType.MODIFIED, "old": old, "new": new, "fields": fields})
        return changes

    def compare(
        self,
        project_id: UUID,
        baseline_mission_revision: int,
        target_mission_revision: int,
        baseline_spacecraft_revision: int,
        target_spacecraft_revision: int,
    ) -> RevisionChangeImpactReport:
        if (
            target_mission_revision < baseline_mission_revision
            or target_spacecraft_revision < baseline_spacecraft_revision
        ):
            raise RevisionImpactRangeError()

        project_key = str(project_id)
        with self._connection() as connection:
            project_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'mission_projects'"
            ).fetchone()
            if project_table is None:
                raise RevisionImpactProjectNotFoundError(project_key)
            project_exists = connection.execute(
                "SELECT 1 FROM mission_projects WHERE project_id = ?", (project_key,)
            ).fetchone()
            if project_exists is None:
                raise RevisionImpactProjectNotFoundError(project_key)

            mission_rows = connection.execute(
                """
                SELECT revision_number, payload_json
                FROM mission_project_revisions
                WHERE project_id = ? AND revision_number IN (?, ?)
                """,
                (project_key, baseline_mission_revision, target_mission_revision),
            ).fetchall()
            mission_by_number = {row["revision_number"]: json.loads(row["payload_json"]) for row in mission_rows}
            if baseline_mission_revision not in mission_by_number or target_mission_revision not in mission_by_number:
                raise RevisionImpactRevisionNotFoundError()

            configuration_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'spacecraft_configurations'"
            ).fetchone()
            if configuration_table is None:
                raise RevisionImpactConfigurationNotFoundError(project_key)
            configuration = connection.execute(
                "SELECT configuration_id FROM spacecraft_configurations WHERE project_id = ?",
                (project_key,),
            ).fetchone()
            if configuration is None:
                raise RevisionImpactConfigurationNotFoundError(project_key)

            spacecraft_rows = connection.execute(
                """
                SELECT revision_number, payload_json
                FROM spacecraft_configuration_revisions
                WHERE configuration_id = ? AND revision_number IN (?, ?)
                """,
                (
                    configuration["configuration_id"],
                    baseline_spacecraft_revision,
                    target_spacecraft_revision,
                ),
            ).fetchall()
            spacecraft_by_number = {
                row["revision_number"]: json.loads(row["payload_json"]) for row in spacecraft_rows
            }
            if (
                baseline_spacecraft_revision not in spacecraft_by_number
                or target_spacecraft_revision not in spacecraft_by_number
            ):
                raise RevisionImpactRevisionNotFoundError()

            allocation_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'requirement_allocations'"
            ).fetchone()
            allocation_rows = []
            if allocation_table is not None:
                allocation_rows = connection.execute(
                    """
                    SELECT allocation_id, requirement_id, component_id
                    FROM requirement_allocations
                    WHERE project_id = ?
                    ORDER BY requirement_id, component_id, allocation_id
                    """,
                    (project_key,),
                ).fetchall()

        baseline_requirements = {
            item["requirement_id"]: item for item in mission_by_number[baseline_mission_revision]["requirements"]
        }
        target_requirements = {
            item["requirement_id"]: item for item in mission_by_number[target_mission_revision]["requirements"]
        }
        baseline_components = {
            item["component_id"]: item for item in spacecraft_by_number[baseline_spacecraft_revision]["components"]
        }
        target_components = {
            item["component_id"]: item for item in spacecraft_by_number[target_spacecraft_revision]["components"]
        }

        requirement_diffs = self._diff_records(
            baseline_requirements, target_requirements
        )
        component_diffs = self._diff_records(
            baseline_components, target_components
        )

        requirement_changes = [
            RequirementRevisionChange(
                requirement_id=item["id"],
                change_type=item["type"],
                baseline_title=item["old"]["title"] if item["old"] else None,
                target_title=item["new"]["title"] if item["new"] else None,
                changed_fields=item["fields"],
            )
            for item in requirement_diffs
        ]
        component_changes = [
            ComponentRevisionChange(
                component_id=item["id"],
                change_type=item["type"],
                baseline_name=item["old"]["name"] if item["old"] else None,
                target_name=item["new"]["name"] if item["new"] else None,
                baseline_subsystem=item["old"]["subsystem"] if item["old"] else None,
                target_subsystem=item["new"]["subsystem"] if item["new"] else None,
                changed_fields=item["fields"],
            )
            for item in component_diffs
        ]

        changed_requirements = {
            item["id"]: item["type"] for item in requirement_diffs
        }
        changed_components = {
            item["id"]: item["type"] for item in component_diffs
        }
        impacted_allocations = []
        for row in allocation_rows:
            reasons = []
            requirement_change = changed_requirements.get(row["requirement_id"])
            component_change = changed_components.get(row["component_id"])
            if requirement_change == RevisionChangeType.REMOVED:
                reasons.append("allocated_requirement_removed")
            elif requirement_change == RevisionChangeType.MODIFIED:
                reasons.append("allocated_requirement_modified")
            if component_change == RevisionChangeType.REMOVED:
                reasons.append("allocated_component_removed")
            elif component_change == RevisionChangeType.MODIFIED:
                reasons.append("allocated_component_modified")
            if reasons:
                impacted_allocations.append(
                    AllocationImpact(
                        allocation_id=UUID(row["allocation_id"]),
                        requirement_id=row["requirement_id"],
                        component_id=row["component_id"],
                        impact_reasons=reasons,
                    )
                )

        return RevisionChangeImpactReport(
            project_id=project_id,
            baseline_mission_revision=baseline_mission_revision,
            target_mission_revision=target_mission_revision,
            baseline_spacecraft_revision=baseline_spacecraft_revision,
            target_spacecraft_revision=target_spacecraft_revision,
            requirement_changes=requirement_changes,
            component_changes=component_changes,
            impacted_allocations=impacted_allocations,
            added_requirement_count=sum(item.change_type == RevisionChangeType.ADDED for item in requirement_changes),
            removed_requirement_count=sum(item.change_type == RevisionChangeType.REMOVED for item in requirement_changes),
            modified_requirement_count=sum(item.change_type == RevisionChangeType.MODIFIED for item in requirement_changes),
            added_component_count=sum(item.change_type == RevisionChangeType.ADDED for item in component_changes),
            removed_component_count=sum(item.change_type == RevisionChangeType.REMOVED for item in component_changes),
            modified_component_count=sum(item.change_type == RevisionChangeType.MODIFIED for item in component_changes),
            limitations=[
                "This report compares stored snapshots; it does not determine whether a design change is technically acceptable.",
                "Current project-scoped allocations are compared with revision differences; allocations are not themselves revisioned.",
                "Historical verification evidence is not replayed or automatically invalidated when a requirement or component changes.",
                "A modified requirement or component requires engineering review; this report does not assign safety or verification impact severity.",
                "Only the specified mission and spacecraft revisions are compared.",
            ],
        )
