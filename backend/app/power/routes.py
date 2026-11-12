from fastapi import APIRouter

from app.power.energy_balance import (
    SimpleEnergyBalanceRequest,
    SimpleEnergyBalanceResult,
    calculate_simple_energy_balance,
)

router = APIRouter(prefix="/models/power", tags=["power-models"])


@router.post("/simple-energy-balance", response_model=SimpleEnergyBalanceResult)
def simple_energy_balance(payload: SimpleEnergyBalanceRequest) -> SimpleEnergyBalanceResult:
    """Calculate a constant-power interval energy balance with explicit limitations."""
    return calculate_simple_energy_balance(payload)
