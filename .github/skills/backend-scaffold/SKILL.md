---
name: backend-scaffold
description: 'Scaffold the AI Interview Tool backend and MVP app structure. Use when creating the initial FastAPI, Streamlit, service, repository, provider, config, and test layout from the architecture and requirements docs.'
argument-hint: 'Describe the scaffold scope or vertical slice to create'
user-invocable: true
---

# Backend Scaffold

## When to Use
- Create the initial project structure for the AI Interview Tool
- Add new FastAPI modules, Streamlit pages, repositories, or service layers
- Start a new vertical slice from the existing requirements and architecture docs

## Required Context
Read these documents before creating or restructuring code:
- `docs/product-requirements.md`
- `docs/application-architecture.md`
- `docs/entity-relationship-diagram.md`
- `docs/evaluation-response-schemas.md`

## Rules
- Keep the stack Python-first.
- Keep Streamlit thin and place business logic behind FastAPI-owned services.
- Separate `auth`, `admin_ingestion`, `interview`, `evaluation`, `retrieval`, `reporting`, `repositories`, and `providers`.
- Keep Bedrock usage behind a provider abstraction.
- Create tests with each new slice instead of deferring all testing.

## Procedure
1. Read the architecture and requirements docs for the target slice.
2. Create only the folders and files needed for that slice.
3. Add typed schemas and domain models before route handlers when possible.
4. Add a narrow validation path such as one unit test or one integration test.
5. Keep placeholders explicit when a later slice will complete the behavior.

## Expected Output
- Minimal folder and file scaffold for the requested slice
- Stubs or implementations aligned to the existing docs
- At least one focused validation artifact or command suggestion