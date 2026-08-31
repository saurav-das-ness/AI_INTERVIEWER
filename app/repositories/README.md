# Repositories Layer

This folder contains persistence contracts and adapters.

- Repositories translate between domain entities and storage.
- They may depend on `app/db/` helpers but should not contain HTTP logic.

Keep orchestration and validation in services, not repositories.
