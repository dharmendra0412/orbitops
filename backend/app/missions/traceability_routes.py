"""Requirement-to-spacecraft traceability API."""
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.missions.traceability import (
    RequirementAllocation,
    RequirementAllocationCreate,
    RequirementTraceabilityMatrix,
)
from app.settings import settings
from app.storage.requirement_traceability import (
    RequirementTraceabilityStore,
    TraceabilityAllocationExistsError,
    TraceabilityComponentNotFoundError,
    TraceabilityConfigurationNotFoundError,
    TraceabilityProjectNotFoundError,
    TraceabilityRequirementNotFoundError,
)

router = APIRouter(
    prefix="/missions/projects/{project_id}/traceability",
    tags=["requirement-traceability"],
)


@lru_cache(maxsize=1)
def get_requirement_traceability_store() -> RequirementTraceabilityStore:
    return RequirementTraceabilityStore(settings.database_path)


@router.post(
    "/allocations",
    response_model=RequirementAllocation,
    status_code=status.HTTP_201_CREATED,
)
def create_requirement_allocation(
    project_id: UUID,
    payload: RequirementAllocationCreate,
    store: Annotated[RequirementTraceabilityStore, Depends(get_requirement_traceability_store)],
) -> RequirementAllocation:
    """Append a requirement-to-component allocation after validating both references."""
    try:
        return store.create(project_id, payload)
    except TraceabilityProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="Mission project not found") from error
    except TraceabilityConfigurationNotFoundError as error:
        raise HTTPException(status_code=409, detail="Spacecraft configuration is required") from error
    except TraceabilityRequirementNotFoundError as error:
        raise HTTPException(status_code=422, detail="Requirement not found in latest mission revision") from error
    except TraceabilityComponentNotFoundError as error:
        raise HTTPException(status_code=422, detail="Component not found in latest spacecraft configuration") from error
    except TraceabilityAllocationExistsError as error:
        raise HTTPException(status_code=409, detail="Requirement is already allocated to this component") from error


@router.get("/matrix", response_model=RequirementTraceabilityMatrix)
def get_requirement_traceability_matrix(
    project_id: UUID,
    store: Annotated[RequirementTraceabilityStore, Depends(get_requirement_traceability_store)],
) -> RequirementTraceabilityMatrix:
    """Build the latest-revision traceability matrix without implying compliance."""
    matrix = store.matrix(project_id)
    if matrix is None:
        raise HTTPException(status_code=404, detail="Mission project not found")
    return matrix
