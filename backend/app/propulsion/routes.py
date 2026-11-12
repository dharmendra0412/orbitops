from typing import Annotated

from fastapi import APIRouter, Depends

from app.propulsion.ideal_rocket import (
    MODEL_ID,
    IdealRocketEquationRequest,
    IdealRocketEquationResult,
    calculate_ideal_delta_v,
)
from app.settings import settings
from app.storage.model_runs import ModelRunStore

router = APIRouter(prefix="/models/propulsion", tags=["propulsion-models"])


def get_model_run_store() -> ModelRunStore:
    return ModelRunStore(settings.database_path)


@router.post("/ideal-delta-v", response_model=IdealRocketEquationResult)
def ideal_delta_v(
    payload: IdealRocketEquationRequest,
    store: Annotated[ModelRunStore, Depends(get_model_run_store)],
) -> IdealRocketEquationResult:
    """Calculate and persist an ideal rocket-equation run with explicit limitations."""
    result = calculate_ideal_delta_v(payload)
    snapshot = store.create(
        model_id=MODEL_ID,
        model_version=result.model_version,
        equation_id=result.equation_id,
        result=result.model_dump(mode="json"),
    )
    return result.model_copy(
        update={"run_id": snapshot.run_id, "created_at": snapshot.created_at}
    )
