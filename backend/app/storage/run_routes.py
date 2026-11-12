from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.settings import settings
from app.storage.model_runs import ModelRunSnapshot, ModelRunStore

router = APIRouter(prefix="/models/runs", tags=["model-run-registry"])


def get_model_run_store() -> ModelRunStore:
    return ModelRunStore(settings.database_path)


@router.get("", response_model=list[ModelRunSnapshot])
def list_model_runs(
    store: Annotated[ModelRunStore, Depends(get_model_run_store)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ModelRunSnapshot]:
    """List persisted model runs newest first."""
    return store.list(limit=limit, offset=offset)


@router.get("/{run_id}", response_model=ModelRunSnapshot)
def get_model_run(
    run_id: str,
    store: Annotated[ModelRunStore, Depends(get_model_run_store)],
) -> ModelRunSnapshot:
    """Retrieve the complete persisted input/output snapshot for one model run."""
    snapshot = store.get(run_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model run not found")
    return snapshot
