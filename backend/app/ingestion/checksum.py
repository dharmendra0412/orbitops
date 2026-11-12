"""Bounded, non-persistent upload integrity inspection."""
from hashlib import sha256
from typing import Annotated

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, Field

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
CHUNK_SIZE_BYTES = 1024 * 1024


class UploadIntegrityResult(BaseModel):
    file_name: Annotated[str, Field(min_length=1, max_length=255)]
    media_type: Annotated[str, Field(min_length=1, max_length=120)]
    file_size_bytes: int
    checksum_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    storage_status: str = "not_persisted"


async def inspect_upload(upload: UploadFile) -> UploadIntegrityResult:
    """Hash an upload in bounded chunks without persisting its contents."""
    file_name = upload.filename
    if not file_name or "/" in file_name or "\\" in file_name or file_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Upload must have a plain file name")

    digest = sha256()
    total_bytes = 0
    try:
        while chunk := await upload.read(CHUNK_SIZE_BYTES):
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Upload exceeds the {MAX_UPLOAD_BYTES}-byte limit",
                )
            digest.update(chunk)
    finally:
        await upload.close()

    if total_bytes == 0:
        raise HTTPException(status_code=422, detail="Empty files cannot be registered")

    return UploadIntegrityResult(
        file_name=file_name,
        media_type=upload.content_type or "application/octet-stream",
        file_size_bytes=total_bytes,
        checksum_sha256=digest.hexdigest(),
    )
