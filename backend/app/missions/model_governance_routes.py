"""Model verification and validation evidence API."""
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.missions.model_governance import (
    ModelAssessment,
    ModelAssessmentCreate,
    ModelGovernanceCatalog,
)
from app.settings import settings
from app.storage.model_governance import (
    ModelAssessmentDatasetNotFoundError,
    ModelDefinitionNotFoundError,
    ModelGovernanceStore,
)

router = APIRouter(prefix="/models/governance", tags=["model-governance"])


@lru_cache(maxsize=1)
def get_model_governance_store() -> ModelGovernanceStore:
    return ModelGovernanceStore(settings.database_path)


@router.get("/catalog", response_model=ModelGovernanceCatalog)
def get_model_governance_catalog(
    store: Annotated[ModelGovernanceStore, Depends(get_model_governance_store)],
) -> ModelGovernanceCatalog:
    """List registered models and credibility states derived from evidence records."""
    return store.catalog()


@router.post(
    "/assessments",
    response_model=ModelAssessment,
    status_code=status.HTTP_201_CREATED,
)
def create_model_assessment(
    payload: ModelAssessmentCreate,
    store: Annotated[ModelGovernanceStore, Depends(get_model_governance_store)],
) -> ModelAssessment:
    """Append verification or validation evidence for a registered model version."""
    try:
        return store.create(payload)
    except ModelDefinitionNotFoundError as error:
        raise HTTPException(
            status_code=422,
            detail="Model ID, version, and equation ID must match the registered model catalogue",
        ) from error
    except ModelAssessmentDatasetNotFoundError as error:
        raise HTTPException(
            status_code=422,
            detail="Reference dataset manifest is not registered",
        ) from error


@router.get("/assessments", response_model=list[ModelAssessment])
def list_model_assessments(
    store: Annotated[ModelGovernanceStore, Depends(get_model_governance_store)],
    model_id: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    model_version: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
) -> list[ModelAssessment]:
    """List immutable model assessment evidence, optionally filtered by model identity."""
    return store.list_assessments(model_id=model_id, model_version=model_version)
