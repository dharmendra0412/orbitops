"""SPICE kernel metadata registration and bounded artifact acquisition API."""
import hashlib
import os
import secrets
import stat
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.ephemeris.frame_transformation import SpiceFrameTransformError, transform_frame
from app.ephemeris.inspection import SpiceInspectionError, inspect_artifact
from app.ephemeris.kernels import (
    SpiceEtToUtcRequest,
    SpiceFrameTransformRecord,
    SpiceFrameTransformRequest,
    SpiceKernelArtifactRecord,
    SpiceKernelInspectionRecord,
    SpiceKernelRecord,
    SpiceKernelRegistration,
    SpiceTimeConversionRecord,
    SpiceUtcToEtRequest,
)
from app.ephemeris.time_conversion import (
    SpiceTimeConversionError,
    convert_et_to_utc,
    convert_utc_to_et,
)
from app.settings import settings
from app.storage.spice_kernels import SpiceKernelAlreadyExistsError, SpiceKernelStore

router = APIRouter(prefix="/ephemeris/spice/kernels", tags=["ephemeris-provenance"])
MAX_KERNEL_UPLOAD_BYTES = 1024 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024


def _supports_secure_artifact_storage() -> bool:
    """Whether this runtime supports the POSIX descriptor-relative storage contract."""
    required_dir_fd_operations = (os.open, os.mkdir, os.link, os.chmod, os.unlink)
    return os.name == "posix" and all(
        operation in os.supports_dir_fd for operation in required_dir_fd_operations
    )


def _open_or_create_storage_directory(parent_fd: int, name: str) -> int:
    """Open a child directory relative to a trusted descriptor without following links."""
    try:
        os.mkdir(name, mode=0o700, dir_fd=parent_fd)
    except FileExistsError:
        pass
    descriptor = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise OSError("SPICE storage component is not a directory")
    return descriptor


def _publish_content_addressed_artifact(
    temporary_name: str,
    staging_fd: int,
    artifact_directory_fd: int,
    *,
    expected_sha256: str,
    expected_size: int,
) -> None:
    """Serialize publication in a pinned digest directory without following links."""
    import fcntl

    try:
        # flock on the pinned directory descriptor avoids a lock-file pathname
        # and serializes deduplication with the publisher's staging-link cleanup.
        fcntl.flock(artifact_directory_fd, fcntl.LOCK_EX)
        os.chmod(temporary_name, 0o444, dir_fd=staging_fd, follow_symlinks=False)
        try:
            os.link(
                temporary_name,
                expected_sha256,
                src_dir_fd=staging_fd,
                dst_dir_fd=artifact_directory_fd,
                follow_symlinks=False,
            )
            return
        except FileExistsError:
            descriptor = os.open(
                expected_sha256,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=artifact_directory_fd,
            )
            with os.fdopen(descriptor, "rb") as existing_file:
                metadata = os.fstat(existing_file.fileno())
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Existing content-addressed artifact must be a singly linked regular file",
                    )
                existing_digest = hashlib.sha256()
                existing_size = 0
                while chunk := existing_file.read(UPLOAD_CHUNK_BYTES):
                    existing_size += len(chunk)
                    existing_digest.update(chunk)
                if existing_size != expected_size or existing_digest.hexdigest() != expected_sha256:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Existing content-addressed artifact failed integrity check",
                    )
                os.fchmod(existing_file.fileno(), 0o444)
    except HTTPException:
        raise
    except OSError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to safely publish or verify the content-addressed artifact",
        ) from error
    finally:
        try:
            os.unlink(temporary_name, dir_fd=staging_fd)
        except FileNotFoundError:
            pass
        finally:
            try:
                fcntl.flock(artifact_directory_fd, fcntl.LOCK_UN)
            except OSError:
                pass


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


@router.post("/{kernel_id}/artifact", response_model=SpiceKernelArtifactRecord,
             status_code=status.HTTP_201_CREATED)
async def upload_spice_kernel_artifact(
    kernel_id: str,
    upload: Annotated[UploadFile, File(description="SPICE kernel binary artifact")],
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
) -> SpiceKernelArtifactRecord:
    """Accept a bounded upload, compute SHA-256, and compare it with registered metadata.

    The server never dereferences the registered source URL. Uploaded bytes are
    stored by their computed digest after the digest matches the user declaration.
    """
    if not _supports_secure_artifact_storage():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Secure SPICE artifact acquisition currently requires a POSIX runtime "
                "with descriptor-relative filesystem operations"
            ),
        )

    registration_record = store.get(kernel_id)
    if registration_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")
    if store.get_artifact(kernel_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Kernel artifact already acquired")

    storage_root = settings.spice_kernel_storage_path
    storage_root.mkdir(parents=True, exist_ok=True)
    root_fd = staging_fd = artifact_parent_fd = None
    temporary_name = f"kernel-{secrets.token_hex(16)}.part"
    digest = hashlib.sha256()
    size_bytes = 0

    try:
        root_fd = os.open(
            storage_root,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        staging_fd = _open_or_create_storage_directory(root_fd, ".staging")
        temporary_fd = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=staging_fd,
        )
        with os.fdopen(temporary_fd, "wb") as destination:
            while chunk := await upload.read(UPLOAD_CHUNK_BYTES):
                size_bytes += len(chunk)
                if size_bytes > MAX_KERNEL_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"Kernel upload exceeds {MAX_KERNEL_UPLOAD_BYTES} byte limit",
                    )
                digest.update(chunk)
                destination.write(chunk)
            destination.flush()
            os.fsync(destination.fileno())

        if size_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Uploaded kernel artifact must not be empty",
            )

        computed_sha256 = digest.hexdigest()
        declared_sha256 = registration_record.registration.sha256
        if computed_sha256 != declared_sha256:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Uploaded artifact SHA-256 does not match the registered digest",
            )

        sha_directory_fd = _open_or_create_storage_directory(root_fd, "sha256")
        try:
            prefix_fd = _open_or_create_storage_directory(sha_directory_fd, computed_sha256[:2])
        finally:
            os.close(sha_directory_fd)
        artifact_parent_fd = prefix_fd
        _publish_content_addressed_artifact(
            temporary_name,
            staging_fd,
            artifact_parent_fd,
            expected_sha256=computed_sha256,
            expected_size=size_bytes,
        )

        storage_key = f"sha256/{computed_sha256[:2]}/{computed_sha256}"
        artifact = SpiceKernelArtifactRecord(
            kernel_id=kernel_id,
            sha256=computed_sha256,
            size_bytes=size_bytes,
            storage_key=storage_key,
            acquired_at=datetime.now(UTC),
        )
        try:
            return store.create_artifact(artifact)
        except SpiceKernelAlreadyExistsError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Kernel artifact was concurrently acquired",
            ) from error
    except HTTPException:
        raise
    except OSError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to safely open or create SPICE artifact storage directories",
        ) from error
    finally:
        if staging_fd is not None:
            try:
                os.unlink(temporary_name, dir_fd=staging_fd)
            except FileNotFoundError:
                pass
            os.close(staging_fd)
        if artifact_parent_fd is not None:
            os.close(artifact_parent_fd)
        if root_fd is not None:
            os.close(root_fd)
        await upload.close()



@router.get("/{kernel_id}/artifact", response_model=SpiceKernelArtifactRecord)
def get_spice_kernel_artifact(
    kernel_id: str,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
) -> SpiceKernelArtifactRecord:
    """Return artifact acquisition metadata, never the binary file itself."""
    if store.get(kernel_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")
    artifact = store.get_artifact(kernel_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE artifact not acquired")
    return artifact


@router.post("/{kernel_id}/inspection", response_model=SpiceKernelInspectionRecord,
             status_code=status.HTTP_201_CREATED)
def inspect_spice_kernel_artifact(
    kernel_id: str,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
) -> SpiceKernelInspectionRecord:
    """Inspect an acquired kernel's declared format and supported index metadata."""
    registration = store.get(kernel_id)
    if registration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")

    artifact = store.get_artifact(kernel_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Acquire the kernel artifact before inspection")

    if store.get_inspection(kernel_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Kernel artifact already inspected")

    try:
        inspection = inspect_artifact(
            kernel_id=kernel_id,
            expected_type=registration.registration.kernel_type.value,
            expected_sha256=artifact.sha256,
            storage_root=settings.spice_kernel_storage_path,
        )
        return store.create_inspection(inspection)
    except SpiceInspectionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except SpiceKernelAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kernel artifact was concurrently inspected",
        ) from error


@router.get("/{kernel_id}/inspection", response_model=SpiceKernelInspectionRecord)
def get_spice_kernel_inspection(
    kernel_id: str,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
) -> SpiceKernelInspectionRecord:
    """Retrieve the immutable result of a completed kernel inspection."""
    if store.get(kernel_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")
    inspection = store.get_inspection(kernel_id)
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kernel inspection not found")
    return inspection

@router.post(
    "/{kernel_id}/time-conversions",
    response_model=SpiceTimeConversionRecord,
    status_code=status.HTTP_201_CREATED,
)
def convert_spice_utc_to_et(
    kernel_id: str,
    payload: SpiceUtcToEtRequest,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
) -> SpiceTimeConversionRecord:
    """Convert an explicitly UTC-tagged instant using one acquired and inspected LSK."""
    registration = store.get(kernel_id)
    if registration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")
    if registration.registration.kernel_type.value != "LSK":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="UTC-to-ET conversion requires a registered LSK kernel",
        )

    artifact = store.get_artifact(kernel_id)
    inspection = store.get_inspection(kernel_id)
    if artifact is None or inspection is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Acquire and inspect the LSK artifact before time conversion",
        )
    if inspection.detected_architecture.upper() != "KPL" or inspection.detected_kernel_type.upper() != "LSK":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The inspected artifact is not a compatible text LSK",
        )

    try:
        conversion = convert_utc_to_et(
            kernel_id=kernel_id,
            utc_time=payload.utc_time,
            expected_sha256=artifact.sha256,
            storage_root=settings.spice_kernel_storage_path,
        )
        return store.create_time_conversion(conversion)
    except SpiceTimeConversionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get(
    "/{kernel_id}/time-conversions",
    response_model=list[SpiceTimeConversionRecord],
)
def list_spice_time_conversions(
    kernel_id: str,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SpiceTimeConversionRecord]:
    """List immutable time-conversion records for one registered kernel."""
    if store.get(kernel_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")
    return store.list_time_conversions(kernel_id, limit=limit, offset=offset)


@router.get(
    "/{kernel_id}/time-conversions/{conversion_id}",
    response_model=SpiceTimeConversionRecord,
)
def get_spice_time_conversion(
    kernel_id: str,
    conversion_id: str,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
) -> SpiceTimeConversionRecord:
    """Retrieve one immutable UTC-to-ET conversion record."""
    if store.get(kernel_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")
    conversion = store.get_time_conversion(conversion_id)
    if conversion is None or conversion.kernel_id != kernel_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE time conversion not found")
    return conversion

@router.post(
    "/{kernel_id}/time-conversions/et-to-utc",
    response_model=SpiceTimeConversionRecord,
    status_code=status.HTTP_201_CREATED,
)
def convert_spice_et_to_utc(
    kernel_id: str,
    payload: SpiceEtToUtcRequest,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
) -> SpiceTimeConversionRecord:
    """Convert finite ET seconds past J2000 TDB using one acquired and inspected LSK."""
    registration = store.get(kernel_id)
    if registration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")
    if registration.registration.kernel_type.value != "LSK":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ET-to-UTC conversion requires a registered LSK kernel",
        )

    artifact = store.get_artifact(kernel_id)
    inspection = store.get_inspection(kernel_id)
    if artifact is None or inspection is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Acquire and inspect the LSK artifact before time conversion",
        )
    if inspection.detected_architecture.upper() != "KPL" or inspection.detected_kernel_type.upper() != "LSK":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The inspected artifact is not a compatible text LSK",
        )

    try:
        conversion = convert_et_to_utc(
            kernel_id=kernel_id,
            et_seconds=payload.et_seconds,
            precision=payload.precision,
            expected_sha256=artifact.sha256,
            storage_root=settings.spice_kernel_storage_path,
        )
        return store.create_time_conversion(conversion)
    except SpiceTimeConversionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

@router.post(
    "/{kernel_id}/frame-transformations",
    response_model=SpiceFrameTransformRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_spice_frame_transformation(
    kernel_id: str,
    payload: SpiceFrameTransformRequest,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
) -> SpiceFrameTransformRecord:
    """Transform positions/states using one acquired, inspected fixed-frame FK."""
    registration = store.get(kernel_id)
    if registration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")
    if registration.registration.kernel_type.value != "FK":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This transformation endpoint requires a registered FK kernel",
        )

    artifact = store.get_artifact(kernel_id)
    inspection = store.get_inspection(kernel_id)
    if artifact is None or inspection is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Acquire and inspect the FK artifact before frame transformation",
        )
    if inspection.detected_architecture.upper() != "KPL" or inspection.detected_kernel_type.upper() != "FK":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The inspected artifact is not a compatible text FK",
        )

    try:
        transformation = transform_frame(
            kernel_id=kernel_id,
            request=payload,
            expected_sha256=artifact.sha256,
            storage_root=settings.spice_kernel_storage_path,
        )
        return store.create_frame_transformation(transformation)
    except SpiceFrameTransformError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get(
    "/{kernel_id}/frame-transformations",
    response_model=list[SpiceFrameTransformRecord],
)
def list_spice_frame_transformations(
    kernel_id: str,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SpiceFrameTransformRecord]:
    """List immutable transformations for one registered FK."""
    if store.get(kernel_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")
    return store.list_frame_transformations(kernel_id, limit=limit, offset=offset)


@router.get(
    "/{kernel_id}/frame-transformations/{transformation_id}",
    response_model=SpiceFrameTransformRecord,
)
def get_spice_frame_transformation(
    kernel_id: str,
    transformation_id: str,
    store: Annotated[SpiceKernelStore, Depends(get_spice_kernel_store)],
) -> SpiceFrameTransformRecord:
    """Retrieve one immutable SPICE frame transformation."""
    if store.get(kernel_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SPICE kernel not found")
    transformation = store.get_frame_transformation(transformation_id)
    if transformation is None or transformation.kernel_id != kernel_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SPICE frame transformation not found",
        )
    return transformation
