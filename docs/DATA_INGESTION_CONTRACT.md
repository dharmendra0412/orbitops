# Scientific Data Ingestion Contract

**Status:** Metadata validation implemented. Dataset downloading, parsing, scientific
interpretation, and source authenticity checks are not implemented.

## Dataset manifest

The API accepts a manifest for one immutable source data product or file. Required
metadata includes provider, product identifier, release/version, source URL,
retrieval timestamp, file name, media type, format, byte size, SHA-256 checksum,
license/terms, and access classification.

Optional metadata includes coordinate reference frame, time system, temporal
coverage, variable-to-unit declarations, and notes. A temporal interval must be
strictly increasing and its endpoints must use compatible timezone awareness.

## Integrity and limits

- SHA-256 is validated as a 64-character hexadecimal string; the API does not
  compute the digest or compare it with downloaded bytes.
- The URL is syntax-validated only. The API does not fetch remote URLs.
- License and access declarations are supplied metadata, not independently verified.
- Coordinate reference frame, time system, and variable units are recorded, not
  interpreted or transformed.
- Unknown fields are rejected to prevent silent acceptance of unsupported claims.
- Synthetic test fixtures are explicitly labelled and must not be represented as
  NASA source data.

## API

POST /api/v1/datasets/manifests/validate

This endpoint validates the manifest contract and returns the normalized metadata.
It does not ingest file bytes or certify scientific suitability.
