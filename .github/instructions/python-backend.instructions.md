---
description: "Use when creating or modifying Python backend, API, Streamlit, evaluation, retrieval, ingestion, auth, or persistence code for the AI Interview Tool. Covers FastAPI service boundaries, Streamlit thin-UI rules, rubric-based scoring, adaptive follow-up logic, and auditability requirements."
name: "AI Interview Python Guidelines"
applyTo: "**/*.py"
---
# AI Interview Python Guidelines

- Keep the codebase Python-first and structure business logic for FastAPI ownership even when the current UI is implemented in Streamlit.
- Keep Streamlit pages thin. Do not place interview orchestration, scoring rules, ingestion logic, or persistence decisions directly in UI handlers.
- Separate concerns into modules such as `auth`, `admin_ingestion`, `interview_orchestration`, `evaluation`, `retrieval`, `persistence`, and `providers`.
- Prefer typed service functions, request/response schemas, and explicit domain models over dictionary-heavy flows.

## Evaluation Flow

- Score candidate answers against question-specific rubric criteria, configured weights, and approved retrieved context.
- Treat retrieval as grounded evidence only from question-linked or topic-linked source content.
- Return structured evaluation results that include score, confidence, strengths, gaps, evidence references, and model metadata.
- If confidence is inside the configured mid-band, trigger up to 3 follow-up questions, capture responses, and rescore.
- Preserve both pre-follow-up and post-follow-up evaluations for auditability.
- Do not reveal the ideal answer during the active interview session.

## Content Ingestion

- Support admin ingestion flows for CSV, Excel, JSON, and PDF-backed context.
- Implement ingestion as validate, preview, persist, and publish rather than direct import-to-live behavior.
- Keep provenance for imported records and document-to-question associations so later scoring can be traced back to source material.
- Use ChromaDB only for retrieval-oriented document chunks and embeddings, not as the primary system of record.

## Data and Persistence

- Use SQLite for transactional MVP data unless the current task explicitly changes the persistence strategy.
- Keep relational data explicit for users, topics, questions, rubrics, sessions, answers, evaluations, and audit events.
- Keep provider-specific payloads and transient prompt artifacts out of the core domain model unless required for audit or replay.

## Provider Integration

- Use LangChain v1 orchestration behind a provider abstraction.
- Default to AWS Bedrock, but do not leak Bedrock-specific logic across business modules.
- Favor deterministic, schema-validated model outputs over free-form text parsing.

## Security and Quality

- Implement email/password authentication and role-aware authorization for `admin` and `candidate` roles.
- Treat auditability, latency, cost control, accessibility, and mobile compatibility as first-class requirements.
- Add focused tests for scoring logic, threshold branching, max-3 follow-up enforcement, ingestion validation, authorization, and audit-log generation.
- Prefer business-rule validation over framework-only smoke coverage.