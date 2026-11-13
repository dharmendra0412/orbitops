"""Mission project workspace API."""
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.missions.projects import (
    MissionProjectDraft,
    MissionProjectRecord,
    MissionProjectSummary,
)
from app.settings import settings
from app.storage.mission_projects import (
    MissionProjectNotFoundError,
    MissionProjectStore,
)

router = APIRouter(prefix="/missions/projects", tags=["mission-projects"])


@lru_cache(maxsize=1)
def get_mission_project_store() -> MissionProjectStore:
    return MissionProjectStore(settings.database_path)


@router.post("", response_model=MissionProjectRecord, status_code=status.HTTP_201_CREATED)
def create_mission_project(
    payload: MissionProjectDraft,
    store: Annotated[MissionProjectStore, Depends(get_mission_project_store)],
) -> MissionProjectRecord:
    """Create a mission workspace and immutable first revision."""
    return store.create(payload)


@router.get("", response_model=list[MissionProjectSummary])
def list_mission_projects(
    store: Annotated[MissionProjectStore, Depends(get_mission_project_store)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MissionProjectSummary]:
    """List mission workspaces, newest activity first."""
    return store.list(limit=limit, offset=offset)


@router.get("/{project_id}", response_model=MissionProjectRecord)
def get_mission_project(
    project_id: UUID,
    store: Annotated[MissionProjectStore, Depends(get_mission_project_store)],
) -> MissionProjectRecord:
    """Retrieve a mission workspace with its latest immutable revision."""
    record = store.get(project_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission project not found")
    return record


@router.post(
    "/{project_id}/revisions",
    response_model=MissionProjectRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_mission_project_revision(
    project_id: UUID,
    payload: MissionProjectDraft,
    store: Annotated[MissionProjectStore, Depends(get_mission_project_store)],
) -> MissionProjectRecord:
    """Append a new revision; prior mission definitions remain unchanged."""
    try:
        return store.create_revision(project_id, payload)
    except MissionProjectNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission project not found",
        ) from error
