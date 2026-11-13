"""Two-body orbital mechanics API with persisted model-run snapshots."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.orbital.mechanics import (
    CircularOrbitRequest,
    EscapeVelocityRequest,
    HOHMANN_DELTA_V_EQUATION_ID,
    HohmannTransferRequest,
    HohmannTransferResult,
    MODEL_ID,
    OrbitalPeriodRequest,
    OrbitalScalarResult,
    VisVivaRequest,
    calculate_circular_velocity,
    calculate_escape_velocity,
    calculate_hohmann_transfer,
    calculate_orbital_period,
    calculate_vis_viva_speed,
)
from app.settings import settings
from app.storage.model_runs import ModelRunStore

router = APIRouter(prefix="/models/orbital-mechanics", tags=["orbital-mechanics"])


def get_orbital_model_run_store() -> ModelRunStore:
    return ModelRunStore(settings.database_path)


def _persist_result(store: ModelRunStore, result, equation_id: str):
    snapshot = store.create(
        model_id=MODEL_ID,
        model_version=result.model_version,
        equation_id=equation_id,
        result=result.model_dump(mode="json"),
    )
    return result.model_copy(
        update={"run_id": snapshot.run_id, "created_at": snapshot.created_at}
    )


@router.post("/circular-orbit", response_model=OrbitalScalarResult)
def circular_orbit(
    payload: CircularOrbitRequest,
    store: Annotated[ModelRunStore, Depends(get_orbital_model_run_store)],
) -> OrbitalScalarResult:
    result = calculate_circular_velocity(payload)
    return _persist_result(store, result, result.equation_id)


@router.post("/vis-viva", response_model=OrbitalScalarResult)
def vis_viva(
    payload: VisVivaRequest,
    store: Annotated[ModelRunStore, Depends(get_orbital_model_run_store)],
) -> OrbitalScalarResult:
    result = calculate_vis_viva_speed(payload)
    return _persist_result(store, result, result.equation_id)


@router.post("/orbital-period", response_model=OrbitalScalarResult)
def orbital_period(
    payload: OrbitalPeriodRequest,
    store: Annotated[ModelRunStore, Depends(get_orbital_model_run_store)],
) -> OrbitalScalarResult:
    result = calculate_orbital_period(payload)
    return _persist_result(store, result, result.equation_id)


@router.post("/escape-velocity", response_model=OrbitalScalarResult)
def escape_velocity(
    payload: EscapeVelocityRequest,
    store: Annotated[ModelRunStore, Depends(get_orbital_model_run_store)],
) -> OrbitalScalarResult:
    result = calculate_escape_velocity(payload)
    return _persist_result(store, result, result.equation_id)


@router.post("/hohmann-transfer", response_model=HohmannTransferResult)
def hohmann_transfer(
    payload: HohmannTransferRequest,
    store: Annotated[ModelRunStore, Depends(get_orbital_model_run_store)],
) -> HohmannTransferResult:
    result = calculate_hohmann_transfer(payload)
    return _persist_result(store, result, HOHMANN_DELTA_V_EQUATION_ID)
