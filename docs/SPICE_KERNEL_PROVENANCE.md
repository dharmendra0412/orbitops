# SPICE kernel provenance, acquisition, and inspection

## Purpose

ORBITOPS records declared kernel provenance before an artifact is used. The acquisition workflow accepts an explicit user upload, computes its digest, compares it with the digest in registered metadata, and stores matching bytes by content hash. The inspection workflow then invokes a pinned CSPICE toolkit in a bounded child process to inspect the file header and selected binary index metadata.

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

- `POST /api/v1/ephemeris/spice/kernels/{kernel_id}/artifact` — multipart upload in field `upload`.
- `GET /api/v1/ephemeris/spice/kernels/{kernel_id}/artifact` — return acquisition metadata; it does not return binary bytes.

The application reads the uploaded file in 1 MiB chunks and enforces a 1 GiB maximum. It writes to a temporary staging file, computes SHA-256 over the received bytes, and compares the computed digest with the registered digest. A mismatch returns HTTP 422 and the staging file is removed. A successful match is moved into content-addressed storage at `sha256/{first-two-hex}/{full-sha256}`; the resulting metadata is appended to SQLite. A kernel can have one acquired artifact record; repeat uploads return HTTP 409.

Configure the storage root with `SPICE_KERNEL_STORAGE_PATH`; the default is `data/spice-kernels`. Deployments should use a dedicated volume with restrictive filesystem permissions, backups, monitoring, and sufficient capacity. Configure an ingress/reverse-proxy request-body limit as well: the application-level limit is not a substitute for an upstream HTTP body-size limit because multipart parsing may spool data before the route processes it.

## Kernel inspection API

- `POST /api/v1/ephemeris/spice/kernels/{kernel_id}/inspection` — inspect an acquired artifact once and append an immutable inspection record.
- `GET /api/v1/ephemeris/spice/kernels/{kernel_id}/inspection` — retrieve that inspection record.

## LSK time conversion API

- `POST /api/v1/ephemeris/spice/kernels/{kernel_id}/time-conversions` — convert one explicitly UTC-tagged input to ET using the selected LSK.
- `POST /api/v1/ephemeris/spice/kernels/{kernel_id}/time-conversions/et-to-utc` — convert finite ET seconds past J2000 TDB to UTC using the selected LSK.
- `GET /api/v1/ephemeris/spice/kernels/{kernel_id}/time-conversions` — list immutable conversion records (paginated).
- `GET /api/v1/ephemeris/spice/kernels/{kernel_id}/time-conversions/{conversion_id}` — retrieve one conversion record.

The UTC-to-ET request body contains `utc_time`, which must be a CSPICE-parseable UTC time string ending in an explicit ` UTC` suffix (for example, `2000 JAN 01 11:58:55.816 UTC`; the API does not promise to accept every ISO-8601 spelling). The ET-to-UTC request body contains finite `et_seconds` and optional output `precision` from 0 through 6 decimal places. Conversion is rejected unless the registration is an LSK, an artifact has been acquired, and the inspection record confirms a `KPL/LSK` text kernel. The service limits LSK conversion artifacts to 10 MiB and re-computes the artifact SHA-256 immediately before invoking a dedicated worker. The worker independently rechecks the size and SHA-256 to narrow the parent/worker time-of-check/time-of-use window, re-checks the kernel architecture/type, furnishes only the selected LSK (never a meta-kernel or arbitrary kernel set), calls CSPICE `str2et` for UTC-to-ET or `et2utc` for ET-to-UTC, and records the direction and original input. It runs with a 12-second timeout and best-effort POSIX resource limits. Each immutable result records the input UTC, ET seconds past J2000 TDB, normalized UTC, exact artifact digest, toolkit version, and conversion timestamp. Conversion history is append-only and queryable by conversion ID.

This is a bounded bidirectional single-LSK time conversion, not an ephemeris query or frame transformation. Correctness depends on the leap-second table and time constants in the exact LSK; the record warns that an LSK may be stale outside its supported date range. The worker's process limits are not a complete OS sandbox.

The optional backend dependency is pinned to `spiceypy==8.4.0` (NAIF CSPICE wrapper). CI installs the `spice` extra so the same toolkit version is exercised in automated tests.

Before parsing, ORBITOPS re-computes the stored artifact SHA-256 and rejects missing, changed, or path-escaped files. It invokes a child Python process with a 12-second wall-clock timeout. On POSIX, the worker applies CPU, address-space, file-size, open-file, and core-dump resource limits. This is process separation with best-effort resource limits, not a complete operating-system sandbox; production deployment still requires a hardened isolated worker/container with no network access and strict filesystem permissions.

CSPICE `getfat` inspects the file architecture and kernel type. A mismatch against the registered family is rejected. For SPK files, the worker extracts object IDs and per-object coverage intervals using CSPICE SPK routines. Coverage is returned as raw ET seconds past J2000 TDB and is not converted to UTC. For binary PCK files, frame class IDs are extracted. For DSK files, object IDs are extracted. Other registered kernel families receive header/type inspection only in this increment.

Meta-kernels are never furnished or loaded. The worker does not call `furnsh`, so a user-supplied meta-kernel cannot cause CSPICE to follow arbitrary local paths. Text-kernel variables, CK inventory/coverage, and full segment-level summaries are not yet extracted. Output collections are capped; truncated results are explicitly flagged.

## Explicit trust boundary

The artifact record uses `checksum_status=matches_user_declared`. This means only that ORBITOPS computed a digest over the uploaded bytes and it equals the value previously declared by the user. It does not establish who published the bytes, whether the source URL is authentic, whether the declared checksum came from a trusted independent channel, or whether the licence/terms are valid. The API does not download from arbitrary URLs, follow redirects, or perform remote network acquisition.

CSPICE successfully identifying a file and extracting index metadata is a structural inspection result, not a scientific validation. Coverage, frames, time-system, and target declarations are not independently compared with authoritative mission requirements. No ephemeris evaluation, frame transformation, trajectory propagation, uncertainty analysis, or mission prediction is implemented by this increment.

Authentication and per-user/team authorization are not implemented in the current application; do not expose artifact upload or inspection as a public or multi-tenant production service.

## Next engineering gates

1. Add independent trusted-digest provenance (for example, separately captured NAIF release manifest/signature evidence where available).
2. Harden worker isolation at deployment level and add a reproducible worker image/build manifest.
3. Expand bounded metadata inspection to CK, text-kernel variables, and segment-level summaries with explicit resource ceilings.
4. Add frame-transformation tests using authoritative NAIF reference vectors and a reviewed kernel set, then build bounded transformations with captured frame and kernel provenance.
5. Only then expose bounded ephemeris queries with provenance, input/output frames, time scales, and kernel set captured in immutable run records.

## Independent NAIF time-reference regression

`backend/tests/fixtures/naif0012_reference.tls` is a compact frozen fixture containing the time-system constants and leap-second table from the official NAIF `naif0012.tls` file. The regression test loads this fixture directly through the pinned SpiceyPy/CSPICE dependency and checks that J2000 12:00:00 TDB maps to ET zero, ET zero formats as 2000-01-01 11:58:55.816 UTC, and parsing that millisecond-formatted UTC instant round-trips to ET zero within 0.5 ms (the output format is rounded to three decimal places). This is an independent reference-data regression for toolkit time conversion, not a new ORBITOPS time-conversion API and not a claim that the 2017 leap-second snapshot is current. Operational use must acquire and inspect an appropriately maintained LSK and capture its exact digest and provenance.

## References

- [Official NAIF `naif0012.tls` source](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls) — source for the frozen fixture's constants and leap-second entries (the source file's table ends at 2017-01-01).
- [SpiceyPy 8.4.0 documentation](https://spiceypy.readthedocs.io/en/main/)
- [SpiceyPy PyPI release and package provenance](https://pypi.org/project/spiceypy/)
- [NAIF SPK Required Reading](https://naif.jpl.nasa.gov/pub/naif/misc/toolkit_docs/C/req/spk.html)
- [NAIF Kernel Required Reading](https://naif.jpl.nasa.gov/pub/naif/misc/toolkit_docs/C/req/kernel.html)

No scientific validation or mission-readiness claim is made.
