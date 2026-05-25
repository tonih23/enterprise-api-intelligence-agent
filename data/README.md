# Synthetic Data Corpus

The `data` directory contains fictional source material for retrieval,
evaluation, and governed-tool demonstrations. It is designed to resemble
enterprise API enablement content without containing real organization,
professional, patient, trial, incident, or credential data.

## Layout

| Directory | Contents |
| --- | --- |
| `docs/` | Fictional catalogue pages, governance and incident runbooks, and architecture notes |
| `api_specs/` | Fake OpenAPI specifications and a fake Postman collection |

## Metadata Convention

Every corpus artifact carries these fields for future ingestion and filtering:

| Field | Meaning |
| --- | --- |
| `domain` | Business capability represented by the artifact |
| `owner` | Fictional accountable team |
| `data_classification` | Synthetic handling label |
| `system` | Fictional source or runtime system |
| `api_name` | API or document collection identifier |
| `version` | Artifact contract version |

Markdown documents place metadata in YAML front matter. OpenAPI documents use
`info.x-agent-metadata`. The Postman collection uses top-level
`x-agent-metadata`.

All hostnames use the reserved `.test` domain, all identifiers and example
values are invented, and placeholder authorization tokens must be supplied at
runtime rather than stored here.
