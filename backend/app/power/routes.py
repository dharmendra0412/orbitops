from typing import Annotated

from fastapi import APIRouter, Depends

from app.power.energy_balance import (
    MODEL_ID,
    SimpleEnergyBalanceRequest,
    SimpleEnergyBalanceResult,
    calculate_simple_energy_balance,
)
from app.propulsion.routes import get_model_run_store
from app.storage.model_runs import ModelRunStore

router = APIRouter(prefix="/models/power", tags=["power-models"])


@router.post("/simple-energy-balance", response_model=SimpleEnergyBalanceResult)
def simple_energy_balance(
    payload: SimpleEnergyBalanceRequest,
    store: Annotated[ModelRunStore, Depends(get_model_run_store)],
) -> SimpleEnergyBalanceResult:
    """Calculate and persist a constant-power interval energy balance."""
    result = calculate_simple_energy_balance(payload)
    snapshot = store.create(
        model_id=MODEL_ID,
        model_version=result.model_version,
        equation_id=result.equation_id,
        result=result.model_dump(mode="json"),
    )
    return result.model_copy(
        update={"run_id": snapshot.run_id, "created_at": snapshot.created_at}
    )
