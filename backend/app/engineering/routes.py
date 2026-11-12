from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.engineering.provenance import EngineeringValue
from app.ingestion.checksum import UploadIntegrityResult, inspect_upload
from app.ingestion.manifests import DatasetManifest

router = APIRouter(prefix="/engineering", tags=["engineering-governance"])
ingestion_router = APIRouter(prefix="/datasets", tags=["scientific-data-ingestion"])


@router.post("/values/validate", response_model=EngineeringValue)
def validate_value_contract(payload: EngineeringValue) -> EngineeringValue:
    """Validate traceability metadata shape; this is not scientific validation."""
    return payload


@ingestion_router.post("/manifests/validate", response_model=DatasetManifest)
def validate_dataset_manifest(payload: DatasetManifest) -> DatasetManifest:
    """Validate dataset manifest structure; no remote data is fetched or trusted."""
    return payload


@ingestion_router.post("/checksum", response_model=UploadIntegrityResult)
async def checksum_dataset_upload(
    file: Annotated[UploadFile, File()],
) -> UploadIntegrityResult:
    """Compute a bounded SHA-256 digest without retaining uploaded file bytes."""
    return await inspect_upload(file)
