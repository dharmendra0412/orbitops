"""Mission/spacecraft revision change-impact API."""
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.missions.revision_impact import RevisionChangeImpactReport
from app.settings import settings
from app.storage.revision_impact import (
    RevisionImpactConfigurationNotFoundError,
    RevisionImpactProjectNotFoundError,
    RevisionImpactRangeError,
    RevisionImpactRevisionNotFoundError,
    RevisionImpactStore,
)

router = APIRouter(
    prefix="/missions/projects/{project_id}/traceability",
    tags=["revision-impact-analysis"],
)


@lru_cache(maxsize=1)
def get_revision_impact_store() -> RevisionImpactStore:
    return RevisionImpactStore(settings.database_path)


@router.get("/change-impact", response_model=RevisionChangeImpactReport)
def get_revision_change_impact(
    project_id: UUID,
    store: Annotated[RevisionImpactStore, Depends(get_revision_impact_store)],
    baseline_mission_revision: Annotated[int, Query(ge=1)],
    target_mission_revision: Annotated[int, Query(ge=1)],
    baseline_spacecraft_revision: Annotated[int, Query(ge=1)],
    target_spacecraft_revision: Annotated[int, Query(ge=1)],
) -> RevisionChangeImpactReport:
    """Compare two immutable mission and spacecraft snapshots and flag affected allocations."""
    try:
        return store.compare(
            project_id,
            baseline_mission_revision,
            target_mission_revision,
            baseline_spacecraft_revision,
            target_spacecraft_revision,
        )
    except RevisionImpactProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail="Mission project not found") from error
    except RevisionImpactConfigurationNotFoundError as error:
        raise HTTPException(status_code=409, detail="Spacecraft configuration not found") from error
    except RevisionImpactRevisionNotFoundError as error:
        raise HTTPException(status_code=404, detail="One or more requested revisions were not found") from error
    except RevisionImpactRangeError as error:
        raise HTTPException(status_code=422, detail="Target revisions must not precede baseline revisions") from error
