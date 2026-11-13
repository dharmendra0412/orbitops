# PDS4 label inspection

ORBITOPS exposes a bounded metadata-only preview for small PDS4 XML labels.

- Endpoint: `POST /api/v1/datasets/pds4/inspect`
- Multipart field: `file`; accepted suffixes: `.xml` and `.lbl`
- Maximum label size: 5 MiB
- DTD/entity declarations are rejected before parsing.
- XML element count and nesting depth are bounded.
- Namespace prefixes are ignored for selected element names.

The response extracts selected Identification_Area fields, selected Observation_Area metadata, and observational file/array descriptors. Referenced science-data files are not uploaded or opened.

This is not authoritative PDS4 schema validation, product consistency checking, scientific data validation, source authentication, coordinate/time-system interpretation, or evidence of scientific suitability. Review and reconcile extracted metadata with the provider's authoritative product documentation before using it in a dataset manifest.
