# Candidate Lunar Data Sources — Technical Review

**Review date:** 2026-11-12  
**Decision:** Candidate sources only. No product, lunar site, coordinate frame, or
science dataset is approved for an ORBITOPS mission model by this review.

## LOLA — Lunar Orbiter Laser Altimeter

The PDS Geosciences Node identifies LOLA product families:
- EDR: raw Experiment Data Records;
- RDR: Reduced Data Records, including calibrated/geolocated observations;
- GDR: Gridded Data Records (maps);
- SHADR: Spherical Harmonic Data Records;
- SLDEM: SELENE/LRO Digital Elevation Model.

The LOLA FAQ recommends GDR for latitude/longitude gridded products and RDR for
individual altimetry tracks at full resolution. EDR is for users performing their
own calibration and geolocation. Product labels and the relevant Software Interface
Specification (SIS) must be reviewed before parsing a selected product.

The Geosciences Node records periodic archive deliveries, while the LOLA Data Node
may be updated more frequently. Its page recorded Release 67 on 2026-09-15, covering
data acquired 2026-03-24 through 2026-06-13. This is a dated archive observation,
not a claim that Release 67 remains the latest release.

Candidate use: elevation/topography context and later terrain analysis. Product
selection, grid resolution, projection, vertical datum, no-data handling, uncertainty,
and site coverage still require review.

Sources:
- [PDS Geosciences Node — LRO LOLA archive](https://pds-geosciences.wustl.edu/missions/lro/lola.htm)
- [PDS Geosciences Node — LOLA FAQ](https://pds-geosciences.wustl.edu/missions/lro/lola_faq.htm)
- [NASA Science — LOLA instrument](https://science.nasa.gov/mission/lro/lola/)

## NASA LRO / LROC data products

NASA's LRO data-products page describes LROC RDR holdings that include global,
polar, regional, shapefile, and topographic products. These are candidates for
surface imagery or supporting terrain context. A specific product and its labels,
projection, resolution, illumination conditions, and usage terms must be reviewed
before integration.

Source:
- [NASA Science — LRO Data Products](https://science.nasa.gov/mission/lro/data-products/)

## Planetary Data System Search API

The PDS Search API supports product discovery, hierarchical archive browsing, and
resolution of product identifiers. It can support curator-led discovery, but PDS
documentation warns that the search servers may not be fully populated with all PDS
datasets. An empty search result must not be treated as proof that a product does
not exist.

The documented API pattern includes the search service under
https://pds.nasa.gov/api/search/1/. Search results must be pinned to an exact product
identifier/version before use in a dataset manifest.

Sources:
- [PDS API Overview](https://nasa-pds.github.io/pds-api/overview.html)
- [PDS Search API Quickstart](https://nasa-pds.github.io/pds-api/guides/search/quickstart.html)
- [PDS Search API User Guide](https://nasa-pds.github.io/pds-api/guides/search.html)

## Integration decision gates

Before a candidate becomes an approved mission input, the curation record must
identify the exact product and version, source label/SIS, license and attribution,
coordinate reference frame, epoch/time system, original units, spatial resolution,
quality/uncertainty, no-data representation, transformation implementation/version,
checksum, and known limitations. The transformed asset must be compared against
source documentation and independent sample checks.

No south-polar landing site or terrain product is selected here. Engineering
analysis must not infer a safe landing site or surface trafficability from the
existence of a topographic dataset alone.
