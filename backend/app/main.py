from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.engineering.routes import router as engineering_router
from app.settings import settings

app = FastAPI(
    title="ORBITOPS API",
    description=(
        "Engineering-grade lunar mission analysis API. "
        "All scientific outputs require traceable inputs and model credibility evidence."
    ),
    version="0.1.0",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

app.include_router(engineering_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["operations"])
def health() -> dict[str, str]:
    """Process liveness only; this endpoint does not certify subsystem readiness."""
    return {"status": "ok", "service": "orbitops-api"}


@app.get("/api/v1/system", tags=["operations"])
def system_info() -> dict[str, str]:
    """Expose product and model-governance posture without claiming model validation."""
    return {
        "product": "ORBITOPS",
        "product_stage": "engineering-foundation",
        "scientific_model_status": "not_yet_released",
        "validation_policy": "evidence_required",
    }
