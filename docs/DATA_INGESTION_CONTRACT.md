# Scientific Data Ingestion Contract

**Status:** Manifest validation and bounded upload hashing are implemented. Dataset
persistence, format decoding, scientific interpretation, and source authenticity
checks are not implemented.

## Dataset manifest

The API accepts a manifest for one immutable source data product or file. Required
metadata includes provider, product identifier, release/version, source URL,
retrieval timestamp, file name, media type, format, byte size, SHA-256 checksum,
license/terms, and access classification.

Optional metadata includes coordinate reference frame, time system, temporal
coverage, variable-to-unit declarations, and notes. A temporal interval must be
strictly increasing; endpoints must both be timezone-aware or both timezone-naive.
Different explicit UTC offsets are supported.

## Upload integrity inspection

POST /api/v1/datasets/checksum

The endpoint streams an uploaded file in 1 MiB chunks, calculates SHA-256, and
returns its filename, media type, byte count, and digest. It enforces a 100 MiB
maximum and rejects empty files and path-like filenames. File bytes are not
persisted; the response explicitly reports storage_status=not_persisted.

The returned digest and file metadata can be copied into a dataset manifest.
This is a checksum of the uploaded bytes, not proof that the source is authentic
or that the dataset is scientifically suitable.

## Integrity and limits

- SHA-256 in a manifest is validated as a 64-character hexadecimal string.
- The URL is syntax-validated only. The API does not fetch remote URLs.
- License and access declarations are supplied metadata, not independently verified.
- Coordinate reference frame, time system, and variable units are recorded, not
  interpreted or transformed.
- Unknown fields are rejected to prevent silent acceptance of unsupported claims.
- Synthetic test fixtures are explicitly labelled and must not be represented as
  NASA source data.

## Manifest API

POST /api/v1/datasets/manifests/validate

This endpoint validates the manifest contract and returns normalized metadata.
It does not ingest or persist file bytes or certify scientific suitability.
