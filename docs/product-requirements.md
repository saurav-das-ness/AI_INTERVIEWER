# Product Requirements Document

## Product Name
AI Interview Tool MVP

## Purpose
Build a deployable AI-assisted interview practice application where candidates answer interview questions and receive context-grounded evaluation, while admins manage question banks, reference material, scoring rules, and reviewable audit data.

## Problem Statement
Candidates need a structured way to practice role-specific interviews and receive meaningful feedback beyond generic chat responses. Administrators need a manageable way to define questions, upload supporting context, configure weighted scoring, and review how the system produced each evaluation.

## Product Goals
- Help candidates practice role-based interview questions with measurable, explainable feedback.
- Allow admins to manage question sets, scoring rubrics, thresholds, and supporting context without code changes.
- Ground answer evaluation in approved context and explicit rubric criteria instead of unconstrained model judgment.
- Preserve a clear audit trail for how answers were scored and when follow-up probing changed the result.
- Deliver an MVP using a Python-first stack that can be deployed on AWS.

## Target Users

### Candidate
- Logs in to the application.
- Selects or is assigned an interview topic or question set.
- Answers questions in a text-based flow.
- Responds to follow-up probing questions when the system needs more evidence.
- Reviews answer-level and session-level feedback.

### Admin
- Logs in with elevated permissions.
- Creates and manages topics and question sets.
- Uploads questions and reference content from CSV, Excel, JSON, and PDF sources.
- Configures rubric criteria, weights, confidence thresholds, and follow-up settings.
- Reviews interview sessions, scores, and audit evidence.

## In Scope for MVP
- Text-based interview sessions.
- Email/password authentication.
- Admin and candidate roles.
- Admin upload and management of question sets.
- Upload of structured question data plus PDF reference material.
- Context-grounded answer evaluation.
- Per-answer score and explanation.
- Confidence-aware follow-up questioning with a maximum of 3 probing questions.
- Session persistence for interviews, answers, scores, and reports.
- Deployable web application with suitable UI.

## Out of Scope for MVP
- Voice interviewing.
- Video or avatar-based interviewing.
- Enterprise SSO.
- Formal hiring recommendations or hiring automation.
- Resume-aware scoring unless explicitly added in a later phase.

## Business Workflow Summary
1. Admin creates a topic or imports a question bank.
2. Admin uploads supporting context and configures rubric weights and thresholds.
3. Candidate starts an interview and submits an answer.
4. The system evaluates the answer against rubric criteria and retrieved evidence.
5. If confidence is in the configured mid-range, the system asks follow-up questions, up to 3 total.
6. The system rescoring step uses the additional answers and stores both initial and final results.
7. Candidate receives answer-level feedback and a session summary.
8. Admin can review the session, scoring evidence, and audit history.

## Functional Requirements

### User and Access Management
- REQ-001: The system must support email/password login for all users.
- REQ-002: The system must support at least two roles: `admin` and `candidate`.
- REQ-003: The system must prevent candidates from accessing admin-only actions and data.

### Admin Topic and Question Management
- REQ-004: Admins must be able to create, edit, publish, and unpublish interview topics.
- REQ-005: Admins must be able to import question sets from CSV, Excel, and JSON.
- REQ-006: Admins must be able to upload PDF documents as supporting reference material.
- REQ-007: The system must validate uploaded content and show import errors before activation.
- REQ-008: The system must preserve provenance for imported questions and reference content.
- REQ-009: Admins must be able to configure rubric criteria and weights for each question or question group.
- REQ-010: Admins must be able to configure confidence thresholds and follow-up limits.

### Candidate Interview Flow
- REQ-011: Candidates must be able to start an interview session for a selected or assigned topic.
- REQ-012: The system must present questions one at a time and capture candidate answers.
- REQ-013: The system must persist the full interview session, including timestamps and answer history.
- REQ-014: The system must allow a candidate to continue the interview until completion of the selected question set.

### Answer Evaluation and Follow-Up Logic
- REQ-015: The system must evaluate answers using question-specific rubric criteria, configured weights, and approved contextual evidence.
- REQ-016: The system must produce a numeric score for each evaluated answer.
- REQ-017: The system must produce strengths and gaps feedback for each evaluated answer.
- REQ-018: The system must produce a confidence value or confidence band for each evaluation.
- REQ-019: If the confidence result falls inside the configured mid-range, the system must generate a follow-up question.
- REQ-020: The system must allow up to 3 follow-up questions for a single primary answer.
- REQ-021: The system must rescore the answer after follow-up responses are captured.
- REQ-022: The system must store both the original evaluation and the final rescored evaluation.
- REQ-023: During the interview session, the system must not reveal the ideal answer directly to the candidate.

### Feedback and Reporting
- REQ-024: The system must store candidate answers and final answer evaluations.
- REQ-025: The system must generate answer-level feedback visible to the candidate.
- REQ-026: The system must generate a session-level summary after interview completion.
- REQ-027: Admins must be able to review interview results, including scores, evidence, and follow-up history.

### Auditability and Traceability
- REQ-028: The system must store retrieved evidence references used during evaluation.
- REQ-029: The system must store applied rubric weights and threshold decisions.
- REQ-030: The system must store model metadata required for review and traceability.
- REQ-031: The system must retain the sequence of follow-up questions and answers used in rescoring.

## Non-Functional Requirements
- NFR-001: The application must provide low-latency answer evaluation suitable for an interactive interview workflow.
- NFR-002: The application must support streamed or progressive status updates so the user can see evaluation progress.
- NFR-003: The application must favor low operating cost through bounded retrieval, configurable model usage, and efficient prompting.
- NFR-004: The application must be mobile-responsive and usable on desktop and mobile browsers.
- NFR-005: The application must preserve accessibility as a first-class UI concern.
- NFR-006: The application must provide auditable evaluation outputs rather than opaque free-form judgments.
- NFR-007: The application must securely store user credentials and protect role-restricted data.

## Technology Constraints and Implementation Direction
- The implementation should use Python as the primary language.
- FastAPI should own the application services and APIs.
- Streamlit should provide the MVP web experience.
- SQLite should store transactional MVP data unless concurrency requirements force a change.
- ChromaDB should store retrieval-oriented document chunks and embeddings.
- LangChain v1 should orchestrate evaluation and retrieval workflows.
- AWS Bedrock should be the default LLM runtime, but the application must keep a provider abstraction so the model backend can change later.

## Data Model Direction
The MVP should model at least the following business entities:
- User
- Topic
- Question
- QuestionContext
- RubricCriterion
- WeightConfig
- InterviewSession
- CandidateAnswer
- FollowUpQuestion
- FollowUpAnswer
- EvaluationResult
- AuditEvent

## Acceptance Criteria Summary
- Admin can upload and validate a topic pack with questions and context.
- Admin can configure weights and threshold bands for follow-up logic.
- Candidate can complete a text-based interview session from login through results.
- The system can score an answer, trigger follow-up questions when confidence is mid-range, and rescore correctly.
- Admin can review the evidence and decision trail behind a score.

## Open Decisions and Risks
- SQLite is acceptable for MVP, but concurrent usage expectations may require a managed relational database later.
- Streamlit is suitable for MVP speed, but future UI expansion may justify a separate frontend while keeping FastAPI as the business layer.
- Resume-based or profile-based contextual scoring is intentionally excluded until privacy, fairness, and scoring policy are defined.

## Recommended Next Documents
- Detailed domain and data model
- API contract and request/response schemas
- Admin upload template specification
- Test strategy and evaluation quality criteria