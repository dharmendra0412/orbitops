"""Mission engineering review package API."""
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from uuid import UUID

from app.missions.review_package import (
    MissionReviewPackage,
    ReviewFinding,
    ReviewPackageState,
    ReviewPackageSummary,
)
from app.missions.spacecraft import calculate_budgets
from app.settings import settings
from app.storage.mission_projects import MissionProjectStore
from app.storage.mission_verification import MissionVerificationStore
from app.storage.requirement_traceability import RequirementTraceabilityStore
from app.storage.spacecraft_configurations import SpacecraftConfigurationStore

router = APIRouter(prefix="/missions/projects/{project_id}", tags=["mission-review-package"])


def get_review_project_store() -> MissionProjectStore:
    return MissionProjectStore(settings.database_path)


def get_review_verification_store() -> MissionVerificationStore:
    return MissionVerificationStore(settings.database_path)


def get_review_traceability_store() -> RequirementTraceabilityStore:
    return RequirementTraceabilityStore(settings.database_path)


def get_review_spacecraft_store() -> SpacecraftConfigurationStore:
    return SpacecraftConfigurationStore(settings.database_path)


@router.get("/review-package", response_model=MissionReviewPackage)
def compile_mission_review_package(
    project_id: UUID,
    project_store: Annotated[MissionProjectStore, Depends(get_review_project_store)],
    verification_store: Annotated[MissionVerificationStore, Depends(get_review_verification_store)],
    traceability_store: Annotated[RequirementTraceabilityStore, Depends(get_review_traceability_store)],
    spacecraft_store: Annotated[SpacecraftConfigurationStore, Depends(get_review_spacecraft_store)],
) -> MissionReviewPackage:
    """Compile project-scoped engineering records without granting acceptance."""
    project = project_store.get(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission project not found")

    verification_records = verification_store.list_for_project(project_id) or []
    spacecraft = spacecraft_store.get(project_id)
    budget = calculate_budgets(spacecraft) if spacecraft is not None else None
    matrix = traceability_store.matrix(project_id)
    if matrix is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission project not found")

    requirements = project.revision.draft.requirements
    evidence_requirement_ids = {item.requirement_id for item in verification_records}
    requirements_without_evidence = sum(
        item.requirement_id not in evidence_requirement_ids for item in requirements
    )
    failed_count = sum(item.outcome.value == "fail" for item in verification_records)
    inconclusive_count = sum(item.outcome.value == "inconclusive" for item in verification_records)
    stale_count = sum(len(item.stale_component_ids) for item in matrix.rows)
    component_count = len(spacecraft.revision.draft.components) if spacecraft is not None else 0

    findings: list[ReviewFinding] = []
    if spacecraft is None:
        findings.append(
            ReviewFinding(
                code="SPACECRAFT_CONFIGURATION_MISSING",
                severity="attention",
                title="Spacecraft configuration is missing",
                description="Create a project-linked spacecraft configuration before conducting subsystem-level review.",
            )
        )
    if matrix.unallocated_requirement_count:
        findings.append(
            ReviewFinding(
                code="REQUIREMENTS_UNALLOCATED",
                severity="attention",
                title="Requirements remain unallocated",
                description=f"{matrix.unallocated_requirement_count} requirement(s) have no active component allocation in the latest configuration.",
            )
        )
    if requirements_without_evidence:
        findings.append(
            ReviewFinding(
                code="VERIFICATION_EVIDENCE_MISSING",
                severity="attention",
                title="Verification evidence is missing",
                description=f"{requirements_without_evidence} requirement(s) have no recorded verification evidence.",
            )
        )
    if stale_count:
        findings.append(
            ReviewFinding(
                code="STALE_COMPONENT_ALLOCATIONS",
                severity="attention",
                title="Stale component allocations require review",
                description=f"{stale_count} allocation reference(s) point to components absent from the latest spacecraft configuration.",
            )
        )
    if failed_count:
        findings.append(
            ReviewFinding(
                code="FAILED_VERIFICATION_EVIDENCE",
                severity="attention",
                title="Failed verification evidence exists",
                description=f"{failed_count} verification record(s) have a fail outcome.",
            )
        )
    if inconclusive_count:
        findings.append(
            ReviewFinding(
                code="INCONCLUSIVE_VERIFICATION_EVIDENCE",
                severity="attention",
                title="Inconclusive verification evidence exists",
                description=f"{inconclusive_count} verification record(s) are inconclusive.",
            )
        )
    if not findings:
        findings.append(
            ReviewFinding(
                code="EVIDENCE_PACKAGE_COMPILED",
                severity="information",
                title="Current project evidence has been compiled",
                description="The basic allocation and evidence presence checks are populated. Independent engineering acceptance is still required.",
            )
        )

    if stale_count or failed_count or inconclusive_count:
        review_state = ReviewPackageState.REVIEW_REQUIRED
    elif (
        spacecraft is None
        or matrix.unallocated_requirement_count > 0
        or requirements_without_evidence > 0
    ):
        review_state = ReviewPackageState.INCOMPLETE
    else:
        review_state = ReviewPackageState.EVIDENCE_COMPILED

    return MissionReviewPackage(
        package_id=uuid4(),
        generated_at=datetime.now(UTC),
        project=project,
        spacecraft_configuration=spacecraft,
        spacecraft_budget=budget,
        traceability_matrix=matrix,
        verification_records=verification_records,
        summary=ReviewPackageSummary(
            requirement_count=len(requirements),
            allocated_requirement_count=matrix.allocated_requirement_count,
            unallocated_requirement_count=matrix.unallocated_requirement_count,
            requirements_without_evidence_count=requirements_without_evidence,
            verification_record_count=len(verification_records),
            failed_verification_record_count=failed_count,
            inconclusive_verification_record_count=inconclusive_count,
            stale_component_reference_count=stale_count,
            spacecraft_component_count=component_count,
        ),
        review_state=review_state,
        findings=findings,
        limitations=[
            "This package compiles project-scoped records for human review; it is not a design approval or readiness certification.",
            "A requirement allocation does not prove component compliance.",
            "Verification evidence outcomes are user-recorded evidence entries and are not independently authenticated or accepted.",
            "Model assessments and dataset manifests are not yet linked to mission projects and are therefore not included.",
            "Mass and power values remain user-supplied bookkeeping inputs; the budget is not an integrated spacecraft simulation.",
            "Authentication, authorization, reviewer independence, and controlled approval signatures are not implemented.",
        ],
    )
