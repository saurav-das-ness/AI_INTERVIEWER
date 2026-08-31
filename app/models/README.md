# Models Layer

This folder separates internal domain models from transport schemas.

- `domain/` contains business entities used by services and repositories.
- `schemas/` contains request and response models for APIs or other boundaries.

Do not mix database access code into model definitions.
