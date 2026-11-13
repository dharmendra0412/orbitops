from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.request_limits import RequestBodyLimitMiddleware

from app.engineering.routes import ingestion_router
from app.engineering.routes import router as engineering_router
from app.ephemeris.routes import router as spice_kernel_router
from app.ingestion.pds4 import router as pds4_router
from app.missions.model_governance_routes import router as model_governance_router
from app.missions.project_evidence_routes import router as project_evidence_router
from app.missions.project_routes import router as mission_projects_router
from app.missions.review_package_routes import router as review_package_router
from app.missions.revision_impact_routes import router as revision_impact_router
from app.missions.routes import router as mission_catalog_router
from app.missions.spacecraft_routes import router as spacecraft_router
from app.missions.traceability_routes import router as traceability_router
from app.missions.verification_routes import router as mission_verification_router
from app.orbital.routes import router as orbital_router
from app.power.routes import router as power_router
from app.propulsion.routes import router as propulsion_router
from app.settings import settings
from app.storage.run_routes import router as model_runs_router

app = FastAPI(
    title="ORBITOPS API",
    description=(
        "Multi-planetary mission engineering platform foundation. "
        "Scientific outputs require traceable inputs and model credibility evidence."
    ),
    version="0.1.0",
)

app.add_middleware(RequestBodyLimitMiddleware)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

app.include_router(engineering_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(pds4_router, prefix="/api/v1")
app.include_router(spice_kernel_router, prefix="/api/v1")
app.include_router(mission_catalog_router, prefix="/api/v1")
app.include_router(mission_projects_router, prefix="/api/v1")
app.include_router(project_evidence_router, prefix="/api/v1")
app.include_router(mission_verification_router, prefix="/api/v1")
app.include_router(spacecraft_router, prefix="/api/v1")
app.include_router(traceability_router, prefix="/api/v1")
app.include_router(revision_impact_router, prefix="/api/v1")
app.include_router(review_package_router, prefix="/api/v1")
app.include_router(propulsion_router, prefix="/api/v1")
app.include_router(orbital_router, prefix="/api/v1")
app.include_router(power_router, prefix="/api/v1")
app.include_router(model_runs_router, prefix="/api/v1")
app.include_router(model_governance_router, prefix="/api/v1")


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
        "scientific_model_status": "unvalidated-models-available",
        "validation_policy": "evidence_required",
        "destination_scope": "eight_planets",
    }
