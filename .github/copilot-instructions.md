# Project Guidelines

## Product Scope
- Build a deployable AI-assisted interview practice application, not a hiring decision engine.
- Treat v1 as text-first. Do not add voice, video, avatar simulation, or enterprise SSO unless explicitly requested.
- Support two roles only unless requirements change: `admin` and `candidate`.
- Preserve the core business flow: admins manage question sets and context, candidates answer questions, the system evaluates answers against weighted rubrics and retrieved context.

## Architecture
- Keep the stack Python-first.
- Use FastAPI for application services and APIs.
- Use Streamlit for the MVP user interface, but keep UI logic thin.
- Keep business logic out of Streamlit pages. Put interview orchestration, evaluation, ingestion, auth, and persistence rules behind service modules that FastAPI can own.
- Use SQLite for transactional MVP data unless concurrency requirements clearly exceed it.
- Use ChromaDB only for retrieval over uploaded reference content and question-linked context.
- Use LangChain v1 orchestration with a provider abstraction. Default to AWS Bedrock, but do not hard-code model-vendor logic outside the provider layer.

## Interview Evaluation Rules
- Evaluate answers against question-specific rubric criteria, configured weights, and retrieved context.
- Every evaluation must produce structured outputs that can be stored and audited: score, confidence, strengths, gaps, evidence, and model metadata.
- If confidence falls inside the configured mid-range, trigger adaptive probing with at most 3 follow-up questions, then rescore.
- Do not reveal the ideal answer during the active interview flow.
- Store both the initial evaluation and the post-follow-up evaluation when rescoring occurs.
- Retrieval must stay grounded to question-linked or topic-linked approved content. Do not mix in unrelated context.

## Admin and Content Rules
- Admin workflows must support question and context ingestion from CSV, Excel, JSON, and PDF.
- Treat ingestion as a validated workflow: parse, preview, report errors, and keep provenance for imported content.
- Keep rubric thresholds, scoring weights, and follow-up settings configurable by admins.
- Model uploads and imports so they can be reviewed before becoming active in candidate interviews.

## Security and Non-Functional Requirements
- Implement email/password authentication and role-based authorization for v1.
- Treat auditability, low latency, low operating cost, accessibility, and mobile responsiveness as first-class requirements.
- Preserve traceability for scoring decisions by storing retrieved evidence, applied weights, threshold decisions, and follow-up history.
- Favor deterministic, schema-validated LLM outputs over free-form responses when implementing evaluation flows.

## Code Organization
- Keep clear module boundaries for `auth`, `admin ingestion`, `interview orchestration`, `evaluation`, `retrieval`, `persistence`, and `provider integration`.
- Prefer small, testable services over large page-level or route-level implementations.
- Keep configuration externalized through environment settings and avoid scattering infrastructure constants through the codebase.

## Testing and Validation
- Add tests for import validation, scoring logic, confidence-threshold branching, follow-up limits, authorization, and audit-log generation.
- Add integration coverage for the end-to-end interview flow and retrieval-grounded evaluation.
- When implementing a feature, prefer validations that prove the business rule rather than only framework-level smoke checks.

## Delivery Bias
- Favor minimal, extensible implementations that satisfy the MVP plan without introducing speculative enterprise complexity.
- If a future-facing feature is needed, add an interface or seam for it rather than shipping the full deferred capability.
- don't create the __pycache__ or other build artifacts in the repository.