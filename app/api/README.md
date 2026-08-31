# API Layer

This folder contains FastAPI-facing contracts.

- `routes/` should stay thin and only translate HTTP requests into service calls.
- `dependencies.py` should wire settings, repositories, and services.

Do not place persistence logic or business rules in route handlers.
