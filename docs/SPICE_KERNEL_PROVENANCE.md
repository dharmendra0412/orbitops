# SPICE kernel provenance and artifact acquisition

## Purpose

ORBITOPS records declared kernel provenance before an artifact is used. The artifact acquisition increment accepts an explicit user upload, computes its digest, compares it with the digest in the registered metadata, and stores matching bytes by content hash. It does not fetch a user-supplied URL.

## Registration contract

Each immutable record captures:

- Stable ORBITOPS kernel identifier and plain file name.
- Kernel family: SPK, PCK, LSK, FK, IK, SCLK, DSK, or MK.
- User-declared source URL, provider, release/version, and licence/terms.
- User-declared SHA-256 digest.
- Optional paired coverage start/end timestamps, each timezone-aware and ordered.
- Declared time system, reference frames, and target names.

Duplicate identifiers return HTTP 409. List operations are paginated. Registration accepts metadata only and never dereferences the source URL.

## Artifact acquisition API

- \`POST /api/v1/ephemeris/spice/kernels/{kernel_id}/artifact\` — multipart upload in field \`upload\`.
- \`GET /api/v1/ephemeris/spice/kernels/{kernel_id}/artifact\` — return acquisition metadata; it does not return binary bytes.

The application reads the uploaded file in 1 MiB chunks and enforces a 1 GiB maximum. It writes to a temporary staging file, computes SHA-256 over the received bytes, and compares the computed digest with the registered digest. A mismatch returns HTTP 422 and the staging file is removed. A successful match is moved into content-addressed storage at \`sha256/{first-two-hex}/{full-sha256}\`; the resulting metadata is appended to SQLite. A kernel can have one acquired artifact record; repeat uploads return HTTP 409.

Configure the storage root with \`SPICE_KERNEL_STORAGE_PATH\`; the default is \`data/spice-kernels\`. The staging directory is beneath this root. Deployments should put this directory on a dedicated volume with restrictive filesystem permissions, backups, monitoring, and sufficient capacity. Configure an ingress/reverse-proxy request-body limit as well: the application-level limit is not a substitute for an upstream HTTP body-size limit because multipart parsing may spool data before the route processes it.

## Explicit trust boundary

The artifact record uses \`checksum_status=matches_user_declared\`. This means only that ORBITOPS computed a digest over the uploaded bytes and it equals the value previously declared by the user. It does not establish who published the bytes, whether the source URL is authentic, whether the declared checksum came from a trusted independent channel, or whether the licence/terms are valid. The API does not download from arbitrary URLs, follow redirects, or perform remote network acquisition.

The uploaded file is untrusted input. It is not parsed or furnished by a SPICE toolkit, and the recorded coverage, frame, time-system, and target metadata are not compared with kernel contents. Authentication and per-user/team authorization are not implemented in the current application; do not expose this endpoint as a public or multi-tenant production upload service.

## Next engineering gates

1. Add independent trusted-digest provenance (for example, a separately captured NAIF release manifest/signature where available) and retain the evidence used for comparison.
2. Inspect file format and kernel metadata using a pinned SPICE toolkit build in an isolated worker with resource limits.
3. Record toolkit build, kernel load order, and inspection outputs in immutable run/evidence records.
4. Add deterministic time conversion and frame transformation tests using authoritative NAIF reference vectors.
5. Only then expose bounded ephemeris queries with provenance, input/output frames, time scales, and kernel set captured in immutable run records.

No kernel parsing, furnishing, ephemeris evaluation, frame transformation, trajectory propagation, or mission prediction is implemented by this increment.
