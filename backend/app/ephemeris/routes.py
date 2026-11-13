"""SPICE kernel metadata registration API."""
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.ephemeris.kernels import SpiceKernelRecord, SpiceKernelRegistration
from app.settings import settings
from app.storage.spice_kernels import SpiceKernelAlreadyExistsError, SpiceKernelStore

router = APIRouter(prefix="/ephemeris/spice/kernels", tags=["ephemeris-provenance"])


@lru_cache(maxsize=1)
def get_spice_kernel_store() -> SpiceKernelStore:
    return SpiceKernelStore(settings.database_path)


@router.post("", response_model=SpiceKernelRecord, status_code=status.HTTP_201_CREATED)
def register_spice_kernel(
    payload: SpiceKernelRegistration,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
) -> SpiceKernelRecord:
    """Register user-declared kernel provenance metadata without fetching the file."""
    try:
        return store.create(payload)
    except SpiceKernelAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"SPICE kernel already registered: {payload.kernel_id}",
        ) from error


@router.get("", response_model=list[SpiceKernelRecord])
def list_spice_kernels(
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SpiceKernelRecord]:
    """List registered SPICE kernel metadata in stable creation order."""
    return store.list(limit=limit, offset=offset)


@router.get("/{kernel_id}", response_model=SpiceKernelRecord)
def get_spice_kernel(
    kernel_id: str,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
) -> SpiceKernelRecord:
    """Retrieve one immutable SPICE kernel registration."""
    record = store.get(kernel_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")
    return record
