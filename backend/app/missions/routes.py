from fastapi import APIRouter

from app.missions.catalog import MissionCatalogResponse, get_mission_catalog

router = APIRouter(prefix="/missions", tags=["mission-catalog"])


@router.get("/catalog", response_model=MissionCatalogResponse)
def mission_catalog() -> MissionCatalogResponse:
    """List planetary destinations and mission archetypes in the current product scope."""
    return get_mission_catalog()
