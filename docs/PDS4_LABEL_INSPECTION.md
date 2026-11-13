# PDS4 label inspection

ORBITOPS exposes a bounded metadata-only preview for small PDS4 XML labels.

- Endpoint: `POST /api/v1/datasets/pds4/inspect`
- Multipart field: `file`; accepted suffixes: `.xml` and `.lbl`
- Maximum label size: 5 MiB
- DTD/entity declarations are rejected before parsing.
- XML element count and nesting depth are bounded.
- Namespace prefixes are ignored for selected element names.

The endpoint accepts only XML documents whose root element is a PDS4 `Product_*` element. The response extracts selected Identification_Area fields, selected Observation_Area metadata, and observational file/array descriptors. Referenced science-data files are not uploaded or opened.

The frontend can copy the extracted title, logical identifier, version, and target/investigation name into the dataset-manifest draft. This is only a convenience: users must verify those fields and still supply the provider, source URL, citation, licence/terms, and a separate checksum for the actual science-data file.

This is not authoritative PDS4 schema validation, product consistency checking, scientific data validation, source authentication, coordinate/time-system interpretation, or evidence of scientific suitability. Review and reconcile extracted metadata with the provider's authoritative product documentation before using it in a dataset manifest.
