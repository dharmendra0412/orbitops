from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.engineering.provenance import EngineeringValue
from app.ingestion.checksum import UploadIntegrityResult, inspect_upload
from app.ingestion.manifests import DatasetManifest
from app.settings import settings
from app.storage.manifests import ManifestAlreadyExistsError, ManifestStore

router = APIRouter(prefix="/engineering", tags=["engineering-governance"])
ingestion_router = APIRouter(prefix="/datasets", tags=["scientific-data-ingestion"])


@lru_cache(maxsize=1)
def get_manifest_store() -> ManifestStore:
    return ManifestStore(settings.database_path)


@router.post("/values/validate", response_model=EngineeringValue)
def validate_value_contract(payload: EngineeringValue) -> EngineeringValue:
    """Validate traceability metadata shape; this is not scientific validation."""
    return payload


@ingestion_router.post("/manifests/validate", response_model=DatasetManifest)
def validate_dataset_manifest(payload: DatasetManifest) -> DatasetManifest:
    """Validate manifest structure without persisting it."""
    return payload


@ingestion_router.post(
    "/manifests",
    response_model=DatasetManifest,
    status_code=status.HTTP_201_CREATED,
)
def create_dataset_manifest(
    payload: DatasetManifest,
    store: Annotated[ManifestStore, Depends(get_manifest_store)],
) -> DatasetManifest:
    """Persist a version-pinned manifest; duplicate IDs are rejected."""
    try:
        return store.create(payload)
    except ManifestAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Manifest already exists: {payload.manifest_id}",
        ) from error


@ingestion_router.get("/manifests", response_model=list[DatasetManifest])
def list_dataset_manifests(
    store: Annotated[ManifestStore, Depends(get_manifest_store)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DatasetManifest]:
    """List registered manifests in stable creation order."""
    return store.list(limit=limit, offset=offset)


@ingestion_router.get("/manifests/{manifest_id}", response_model=DatasetManifest)
def get_dataset_manifest(
    manifest_id: str,
    store: Annotated[ManifestStore, Depends(get_manifest_store)],
) -> DatasetManifest:
    """Retrieve one immutable manifest by its stable identifier."""
    manifest = store.get(manifest_id)
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not found")
    return manifest


@ingestion_router.post("/checksum", response_model=UploadIntegrityResult)
async def checksum_dataset_upload(
    file: Annotated[UploadFile, File()],
) -> UploadIntegrityResult:
    """Compute a bounded SHA-256 digest without retaining uploaded file bytes."""
    return await inspect_upload(file)
