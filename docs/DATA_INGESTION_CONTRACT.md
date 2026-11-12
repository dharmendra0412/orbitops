# Scientific Data Ingestion Contract

**Status:** Dataset manifest validation, SQLite metadata persistence, and bounded
upload hashing are implemented. Dataset-byte persistence, format decoding,
scientific interpretation, and source authenticity checks are not implemented.

## Dataset manifest

The API accepts a manifest for one immutable source data product or file. Required
metadata includes provider, product identifier, release/version, source URL,
citation text, retrieval timestamp, file name, media type, format, byte size,
SHA-256 checksum, license/terms, and access classification.

The manifest records whether the asset is a source, transformed, or derived file.
Transformed and derived assets require both a transformation description and a
transform version. Original units, variable units, coordinate reference frame,
time system, temporal coverage, spatial resolution, uncertainty/quality notes,
limitations, and the property represented by the asset can be recorded where known.
Unknown metadata is left absent rather than invented.

Temporal coverage must be strictly increasing. Endpoints must both be timezone-aware
or both timezone-naive; different explicit UTC offsets are supported. Spatial
resolution value and unit must be supplied together.

## Upload integrity inspection

POST /api/v1/datasets/checksum

The endpoint streams an uploaded file in 1 MiB chunks, calculates SHA-256, and
returns its filename, media type, byte count, and digest. It enforces a 100 MiB
maximum and rejects empty files and path-like filenames. File bytes are not
persisted; the response explicitly reports storage_status=not_persisted.

The returned digest and file metadata can be copied into a dataset manifest.
This is a checksum of the uploaded bytes, not proof that the source is authentic
or that the dataset is scientifically suitable.

## Manifest registry

- POST /api/v1/datasets/manifests/validate validates metadata only.
- POST /api/v1/datasets/manifests stores an immutable manifest in SQLite.
- GET /api/v1/datasets/manifests lists records with limit and offset.
- GET /api/v1/datasets/manifests/{manifest_id} retrieves one record.

Manifest identifiers are unique. Duplicate IDs return HTTP 409; records are not
silently overwritten. SQLite stores manifest JSON and indexing metadata only, not
dataset file bytes. See MANIFEST_REGISTRY.md for schema and persistence details.

## Integrity and limits

- SHA-256 in a manifest is validated as a 64-character hexadecimal string.
- The URL is syntax-validated only. The API does not fetch remote URLs.
- License and access declarations are supplied metadata, not independently verified.
- Coordinate reference frame, time system, and variable units are recorded, not
  interpreted or transformed.
- Unknown fields are rejected to prevent silent acceptance of unsupported claims.
- Synthetic test fixtures are explicitly labelled and must not be represented as
  NASA source data.
- Persistence provides repeatable metadata retrieval, not scientific validation,
  product authenticity, or data suitability.
