# Services Layer

This folder contains the backend business slices.

- `auth/` handles login and role-aware access foundations.
- `ingestion/` will handle upload validation, preview, and publish flows.
- `interview/` will handle session progression.
- `evaluation/` will handle rubric scoring and follow-up branching.
- `retrieval/` will handle grounded context access.
- `reporting/` will build candidate and admin outputs.
- `audit/` will preserve traceability data.

Each service should remain focused and testable.
