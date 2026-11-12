from fastapi import APIRouter

from app.propulsion.ideal_rocket import (
    IdealRocketEquationRequest,
    IdealRocketEquationResult,
    calculate_ideal_delta_v,
)

router = APIRouter(prefix="/models/propulsion", tags=["propulsion-models"])


@router.post("/ideal-delta-v", response_model=IdealRocketEquationResult)
def ideal_delta_v(payload: IdealRocketEquationRequest) -> IdealRocketEquationResult:
    """Calculate ideal rocket-equation delta-v with explicit model limitations."""
    return calculate_ideal_delta_v(payload)
