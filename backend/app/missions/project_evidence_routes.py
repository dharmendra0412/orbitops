"""Mission project evidence association API."""
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.missions.project_evidence import (
    MissionDatasetLink,
    MissionDatasetLinkCreate,
    MissionModelAssessmentLink,
    MissionModelAssessmentLinkCreate,
)
from app.settings import settings
from app.storage.mission_evidence import (
    MissionEvidenceAssessmentNotFoundError,
    MissionEvidenceDatasetNotFoundError,
    MissionEvidenceLinkExistsError,
    MissionEvidenceProjectNotFoundError,
    MissionEvidenceStore,
)

router = APIRouter(
    prefix="/missions/projects/{project_id}/evidence",
    tags=["mission-evidence-associations"],
)


@lru_cache(maxsize=1)
def get_mission_evidence_store() -> MissionEvidenceStore:
    return MissionEvidenceStore(settings.database_path)


@router.post(
    "/datasets",
    response_model=MissionDatasetLink,
    status_code=status.HTTP_201_CREATED,
)
def link_dataset_manifest(
    project_id: UUID,
    payload: MissionDatasetLinkCreate,
    store: Annotated[MissionEvidenceStore, Depends(get_mission_evidence_store)],
) -> MissionDatasetLink:
    """Associate a registered immutable dataset manifest with a mission project."""
    try:
        return store.create_dataset_link(project_id, payload)
    except MissionEvidenceProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="Mission project not found") from error
    except MissionEvidenceDatasetNotFoundError as error:
        raise HTTPException(status_code=404, detail="Dataset manifest not found") from error
    except MissionEvidenceLinkExistsError as error:
        raise HTTPException(status_code=409, detail="Dataset manifest is already linked to this project") from error


@router.get("/datasets", response_model=list[MissionDatasetLink])
def list_project_dataset_links(
    project_id: UUID,
    store: Annotated[MissionEvidenceStore, Depends(get_mission_evidence_store)],
) -> list[MissionDatasetLink]:
    """List dataset manifests linked to one mission project."""
    links = store.list_dataset_links(project_id)
    if links is None:
        raise HTTPException(status_code=404, detail="Mission project not found")
    return links


@router.post(
    "/model-assessments",
    response_model=MissionModelAssessmentLink,
    status_code=status.HTTP_201_CREATED,
)
def link_model_assessment(
    project_id: UUID,
    payload: MissionModelAssessmentLinkCreate,
    store: Annotated[MissionEvidenceStore, Depends(get_mission_evidence_store)],
) -> MissionModelAssessmentLink:
    """Associate an existing model assessment record with a mission project."""
    try:
        return store.create_model_assessment_link(project_id, payload)
    except MissionEvidenceProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="Mission project not found") from error
    except MissionEvidenceAssessmentNotFoundError as error:
        raise HTTPException(status_code=404, detail="Model assessment not found") from error
    except MissionEvidenceLinkExistsError as error:
        raise HTTPException(status_code=409, detail="Model assessment is already linked to this project") from error


@router.get("/model-assessments", response_model=list[MissionModelAssessmentLink])
def list_project_model_assessment_links(
    project_id: UUID,
    store: Annotated[MissionEvidenceStore, Depends(get_mission_evidence_store)],
) -> list[MissionModelAssessmentLink]:
    """List model assessment records linked to one mission project."""
    links = store.list_model_assessment_links(project_id)
    if links is None:
        raise HTTPException(status_code=404, detail="Mission project not found")
    return links
