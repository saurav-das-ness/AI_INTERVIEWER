
## Plan: AI Interview Tool MVP

Build a deployable, text-first AI-assisted interview application where admins upload/manage question sets plus supporting context, and candidates answer questions that are scored against weighted rubrics and retrieved evidence. The recommended MVP stack is Python with FastAPI for core services, Streamlit for the web UI, SQLite for transactional data, ChromaDB for contextual retrieval over uploaded documents, and LangChain v1 with AWS Bedrock behind a provider abstraction. The workspace currently only contains Readme.md, so the implementation plan assumes an initial scaffold will be created.

**Steps**
1. Freeze the v1 requirements and domain model for admin, candidate, interview session, question context, rubric weights, confidence thresholds, follow-up questions, and audit records. This blocks downstream implementation.
2. Define which data belongs in SQLite versus ChromaDB, including how uploaded PDFs and question-linked reference content are chunked, indexed, and traced back to source.
3. Scaffold the Python application with FastAPI, shared config, logging, secrets handling, and a Bedrock-first LLM provider abstraction. This depends on step 1.
4. Implement email/password auth and role separation for admin versus candidate. This can run in parallel with later admin UI work once the app skeleton exists.
5. Build admin content management for topic creation, bulk upload of CSV/Excel/JSON, PDF ingestion, rubric/weight configuration, threshold configuration, validation previews, and publish/unpublish control.
6. Implement the candidate interview flow: question presentation, answer capture, context-grounded evaluation, score/weight/confidence calculation, and persistence of each answer event.
7. Add the adaptive probing loop: if confidence lands in the configured mid-band, ask up to 3 AI-generated follow-up questions, capture responses, then rescore and preserve both initial and final judgments.
8. Generate explainable outputs per answer and per session, including numeric score, strengths/gaps, retrieved evidence, confidence, and audit metadata without revealing the ideal answer during the live session.
9. Build the Streamlit UI for candidate and admin workflows, including streamed progress/status updates and mobile-responsive checks.
10. Package for AWS deployment, then harden for non-functional requirements: latency, low operating cost, auditability, accessibility, and observability.

**Relevant files**
- Readme.md — expand into product overview, architecture, setup, deployment notes, and upload-format guidance.
- Planned scaffold under the project root:
  FastAPI application entrypoint, auth module, admin ingestion module, interview orchestration service, evaluation service, retrieval service, persistence models, Streamlit UI pages, prompt/config assets, and automated tests.

**Verification**
1. Validate four business flows with stakeholders: admin uploads a topic pack, admin configures rubric thresholds, candidate completes a normal answer, candidate enters the follow-up loop and receives a rescored result.
2. Add automated tests for import parsing, rubric weighting, confidence-threshold branching, max-3 follow-up enforcement, session persistence, and audit-log creation.
3. Add integration tests proving retrieval-augmented evaluation uses only question-linked context and returns structured scoring output.
4. Run latency checks for answer evaluation with and without follow-up probing.
5. Run authorization tests proving candidates cannot access admin functions.
6. Validate an AWS deployment with sample data and test the UI on desktop and mobile.

**Decisions**
- Included in v1: text interviewing, admin-managed question banks, context-grounded scoring, adaptive follow-ups, saved reports, email/password login, AWS deployment.
- Deferred from v1: voice, video/avatar simulation, enterprise SSO.
- Recommended architecture: FastAPI owns the business logic; Streamlit is the fastest MVP UI; Bedrock is the default model runtime, but only through a provider abstraction.
- Scope boundary: this is an interview-readiness evaluation tool, not a hiring-decision engine.

**Further considerations**
1. Keep Streamlit for MVP speed, but isolate all business logic in FastAPI so a richer frontend can replace it later without changing scoring.
2. Exclude candidate resumes from v1 unless you want resume-aware scoring explicitly, because it expands privacy and bias risk.
3. Revisit SQLite before broad rollout if you expect meaningful concurrent usage.

I saved the full plan in session memory for handoff. If you want, I can refine this next into one of these:
1. User stories and acceptance criteria
2. Detailed data model and API plan
3. AWS deployment architecture and NFR checklist