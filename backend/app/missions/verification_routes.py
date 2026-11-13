"""Requirement verification evidence API."""
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.missions.verification import VerificationRecord, VerificationRecordCreate
from app.settings import settings
from app.storage.mission_verification import (
    MissionVerificationStore,
    VerificationMethodMismatchError,
    VerificationProjectNotFoundError,
    VerificationRequirementNotFoundError,
)

router = APIRouter(
    prefix="/missions/projects/{project_id}/verification-records",
    tags=["mission-verification"],
)


@lru_cache(maxsize=1)
def get_mission_verification_store() -> MissionVerificationStore:
    return MissionVerificationStore(settings.database_path)


@router.post("", response_model=VerificationRecord, status_code=status.HTTP_201_CREATED)
def create_verification_record(
    project_id: UUID,
    payload: VerificationRecordCreate,
    store: Annotated[MissionVerificationStore, Depends(get_mission_verification_store)],
) -> VerificationRecord:
    """Append evidence for a requirement in the project's latest revision."""
    try:
        return store.create(project_id, payload)
    except VerificationProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="Mission project not found") from error
    except VerificationRequirementNotFoundError as error:
        raise HTTPException(
            status_code=422,
            detail="Requirement is not present in the latest mission project revision",
        ) from error
    except VerificationMethodMismatchError as error:
        raise HTTPException(
            status_code=422,
            detail="Verification method does not match the requirement definition",
        ) from error


@router.get("", response_model=list[VerificationRecord])
def list_verification_records(
    project_id: UUID,
    store: Annotated[MissionVerificationStore, Depends(get_mission_verification_store)],
) -> list[VerificationRecord]:
    """List append-only verification evidence for one mission project."""
    records = store.list_for_project(project_id)
    if records is None:
        raise HTTPException(status_code=404, detail="Mission project not found")
    return records
