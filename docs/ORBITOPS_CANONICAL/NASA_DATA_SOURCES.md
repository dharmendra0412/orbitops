# ORBITOPS — NASA/JPL Data Sources and Integration

## Integration policy

NASA/JPL data enriches context and selected scenario inputs; gameplay must not require live connectivity. Ingest only data needed for the fixed MVP site and provide a manifest with source URL, product ID, retrieval time, version, checksum, coordinate/time reference, transformations, license/credit notes and quality limitations. Keep raw/source and transformed assets distinguishable. Re-review source terms and attribution at ingestion time. A primary-source link is not proof that every derived value is suitable for a game model.

## Candidate sources

| Source | Proposed use | Integration approach and caveat |
|---|---|---|
| NASA Lunar Reconnaissance Orbiter Camera (LROC) and LOLA / PDS | Textural imagery, polar maps/topography and context for selected sites. | Download curated products during preparation; transform to lightweight tiles/height or illumination data; store versioned asset and citation. PDS archives multiple product types; read product labels and SIS before interpreting. [LRO data products](https://science.nasa.gov/mission/lro/data-products/), [LOLA archive information](https://pds-geosciences.wustl.edu/missions/lro/lola.htm). |
| NASA SVS lunar south pole illumination visualization / NASA illumination material | Explain moving long shadows and site trade-offs; possible reference to precomputed schedule. | Use as educational reference, not direct time-series input unless data product and method are explicitly identified. [NASA SVS](https://science.nasa.gov/resource/shadows-near-the-moons-south-pole/), [South Pole Illumination Map](https://science.nasa.gov/photojournal/south-pole-illumination-map/). |
| JPL NAIF SPICE | Later high-fidelity geometry, frames, epochs and spacecraft/planet ephemerides where appropriate kernels exist. | Offline kernel bundles with version/checksum and license/attribution notes. Python wrapper choice and deployment compatibility require evaluation. Not required for MVP. [NAIF Toolkit](https://naif.jpl.nasa.gov/naif/toolkit.html), [SPICE introduction](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/info/intrdctn.html). |
| JPL Horizons API | Offline generation/checking of celestial ephemeris for educational orbit visualizations. | Backend ingestion job or build-time data preparation, never synchronous run dependency; save query parameters and response. [Horizons API](https://ssd-api.jpl.nasa.gov/doc/horizons.html). |
| NASA PDS APIs | Product discovery and metadata lookup. | Use search/catalog API during curation; pin products rather than query per player. [PDS API overview](https://nasa-pds.github.io/pds-api/overview.html), [PDS standards](https://pds.nasa.gov/datastandards/). |

## MVP recommendation

MVP site status: **NOT YET APPROVED**. Begin with exactly one named south-polar site preset only after R1 selects and approves the site and dataset (or explicitly approves an illustrative schedule). Do not invent a site. The eventual briefing may use curated public imagery or a simple stylized surface and a pedagogical illumination schedule whose resolution and limitations are displayed. Do not derive a scientifically asserted illumination percentage from a visualization screenshot. If a suitable gridded product cannot be validated in time, use clearly illustrative schedule values and source only the qualitative rationale. Communication windows can be scenario-authored illustrative game inputs pending validated geometry.

## Ingestion and cache pipeline

1. Curator records source, product identifier, access date, data terms and desired game use.
2. Download outside gameplay; verify archive labels/format and checksum; retain source file or stable archive reference.
3. Transform with documented script/version and coordinate/time metadata; preserve units and no-data masks.
4. Review transformations and compare sample locations to source viewer/documentation.
5. Publish immutable manifest and asset; pin manifest in scenario version.
6. Runtime reads only stored manifest/assets. Refresh creates a new manifest and scenario version; existing missions and runs retain prior references.

## Provenance record fields

`source_id`, `institution`, `title`, `product_id`, `url`, `retrieved_at`, `source_release`, `license_or_terms`, `citation_text`, `property_or_asset`, `original_units`, `transformation`, `transform_version`, `coordinate_frame`, `epoch/time_system`, `spatial_resolution`, `uncertainty_or_quality`, `limitations`, `checksum`.

## Scientific caveats

NASA describes south-polar illumination as dependent on local terrain, with some crater interiors permanently shadowed and nearby ridges more illuminated. Water-ice evidence is complex and should not imply every shadowed site contains accessible ice. ORBITOPS objectives represent reconnaissance/science return, not confirmed resource extraction. See [NASA lunar south pole environment](https://www.nasa.gov/reference/moonbase-environment/) and [NASA Moon water and ices](https://science.nasa.gov/moon/moon-water-and-ices/).

## Final MVP use

After R1 approval, the stationary lander will use exactly one selected named site preset and a 720-entry fixed-step schedule pinned in the environment manifest. Until then, the actual site and dataset are **NOT YET APPROVED**. The manifest also pins sub-hour contact/operation windows and the 720 illustrative/source-labeled heater request and survival-minimum schedules; the latter are educational power-demand inputs, not a thermal solver. NASA/JPL data is obtained and reviewed before deployment, cached, checksummed and cited; gameplay does not call live endpoints. Until a suitable product is curated and transformations reviewed, illumination, temperature display values and contacts must be labeled `illustrative`, not presented as NASA measurements. Do not infer measured illumination from a visualization image. LRO/LROC/LOLA and PDS products remain candidate source assets; site and product selection require human/domain review.

