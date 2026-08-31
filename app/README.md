# App Layer

This folder contains the backend application package.

- `api/` holds FastAPI routes and dependency wiring.
- `core/` holds settings and security helpers.
- `db/` holds low-level database setup helpers.
- `models/` holds domain and transport models.
- `providers/` is reserved for Bedrock and vector integrations.
- `repositories/` holds persistence adapters and contracts.
- `services/` holds business logic slices.
- `utils/` is reserved for shared helper functions that do not fit a domain service.

Business logic should live in `services/`, not in route handlers.
