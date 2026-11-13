# SPICE kernel provenance registry

## Purpose

The first SPICE integration increment creates a traceable metadata registry before any kernel binaries are downloaded or used in calculations. This supports reproducibility and makes the declared provenance visible for later engineering review.

## Registration contract

Each immutable record captures:

- Stable ORBITOPS kernel identifier and plain file name.
- Kernel family: SPK, PCK, LSK, FK, IK, SCLK, DSK, or MK.
- User-declared source URL, provider, release/version, and licence/terms.
- User-declared SHA-256 digest.
- Optional paired coverage start/end timestamps, each timezone-aware and ordered.
- Declared time system, reference frames, and target names.

Duplicate identifiers return HTTP 409. List operations are paginated. The API accepts metadata only and does not fetch the source URL.

## API

- `POST /api/v1/ephemeris/spice/kernels`
- `GET /api/v1/ephemeris/spice/kernels?limit=50&offset=0`
- `GET /api/v1/ephemeris/spice/kernels/{kernel_id}`

## Explicit trust boundary

The returned status is `user_declared_unverified`. ORBITOPS has not computed the supplied digest, authenticated the provider or terms, downloaded or stored the binary, parsed the kernel, checked actual coverage, or validated frame/time-system declarations. A valid metadata record is not evidence that a kernel is genuine, safe, complete, or scientifically suitable.

## Next engineering gates

1. Add a controlled artifact acquisition path with strict host allowlists, size limits, redirect policy, and content-addressed storage.
2. Compute SHA-256 over the acquired bytes and compare it with an independently sourced trusted digest where available.
3. Inspect kernel type and metadata with a pinned SPICE toolkit build; record toolkit and kernel versions.
4. Add deterministic time conversion and frame transformation tests using authoritative NAIF reference vectors.
5. Only then expose bounded ephemeris queries, with kernel load order, provenance, and all input/output frames and time scales captured in immutable run records.

No trajectory propagation, ephemeris evaluation, frame transformation, or mission prediction is implemented by this increment.
