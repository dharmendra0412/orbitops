"""Spacecraft configuration and budget API."""
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.missions.spacecraft import (
    SpacecraftBudgetSummary,
    SpacecraftConfigurationDraft,
    SpacecraftConfigurationRecord,
    calculate_budgets,
)
from app.settings import settings
from app.storage.spacecraft_configurations import (
    SpacecraftConfigurationNotFoundError,
    SpacecraftConfigurationStore,
    SpacecraftProjectNotFoundError,
)

router = APIRouter(prefix="/missions/projects/{project_id}/spacecraft", tags=["spacecraft-configuration"])


@lru_cache(maxsize=1)
def get_spacecraft_configuration_store() -> SpacecraftConfigurationStore:
    return SpacecraftConfigurationStore(settings.database_path)


@router.post(
    "/configuration",
    response_model=SpacecraftConfigurationRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_spacecraft_configuration(
    project_id: UUID,
    payload: SpacecraftConfigurationDraft,
    store: Annotated[SpacecraftConfigurationStore, Depends(get_spacecraft_configuration_store)],
) -> SpacecraftConfigurationRecord:
    """Create the first spacecraft configuration snapshot for a mission project."""
    try:
        return store.create(project_id, payload)
    except SpacecraftProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="Mission project not found") from error
    except Exception as error:
        if "UNIQUE constraint failed" in str(error):
            raise HTTPException(status_code=409, detail="Spacecraft configuration already exists") from error
        raise


@router.get("/configuration", response_model=SpacecraftConfigurationRecord)
def get_spacecraft_configuration(
    project_id: UUID,
    store: Annotated[SpacecraftConfigurationStore, Depends(get_spacecraft_configuration_store)],
) -> SpacecraftConfigurationRecord:
    """Retrieve the latest configuration snapshot."""
    record = store.get(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Spacecraft configuration not found")
    return record


@router.post(
    "/configuration/revisions",
    response_model=SpacecraftConfigurationRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_spacecraft_configuration_revision(
    project_id: UUID,
    payload: SpacecraftConfigurationDraft,
    store: Annotated[SpacecraftConfigurationStore, Depends(get_spacecraft_configuration_store)],
) -> SpacecraftConfigurationRecord:
    """Append a new configuration revision without overwriting earlier snapshots."""
    try:
        return store.create_revision(project_id, payload)
    except SpacecraftProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="Mission project not found") from error
    except SpacecraftConfigurationNotFoundError as error:
        raise HTTPException(status_code=404, detail="Spacecraft configuration not found") from error


@router.get("/budgets", response_model=SpacecraftBudgetSummary)
def get_spacecraft_budgets(
    project_id: UUID,
    store: Annotated[SpacecraftConfigurationStore, Depends(get_spacecraft_configuration_store)],
) -> SpacecraftBudgetSummary:
    """Return transparent mass and average-power bookkeeping for the latest revision."""
    record = store.get(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Spacecraft configuration not found")
    return calculate_budgets(record)
