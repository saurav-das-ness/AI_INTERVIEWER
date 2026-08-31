# Application Architecture

This document captures the target MVP architecture for the AI Interview Tool based on the current product requirements, upload specifications, and evaluation schema contracts. It shows both the high-level runtime architecture and the main component relationships inside the application.

## Application Architecture

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
```mermaid
flowchart TD
    subgraph ClientLayer["Client Layer"]
        Browser["Web Browser"]
        StreamlitUi["Streamlit UI"]
    end

    subgraph ApiLayer["Application Layer - FastAPI"]
        AuthApi["Auth API"]
        AdminApi["Admin Content API"]
        InterviewApi["Interview API"]
        ReportApi["Report API"]
    end

    subgraph ServiceLayer["Domain Services"]
        AuthSvc["Auth Service"]
        IngestSvc["Ingestion Service"]
        Orchestrator["Interview Orchestrator"]
        EvalSvc["Evaluation Service"]
        FollowupSvc["Followup Service"]
        RetrievalSvc["Retrieval Service"]
        ReportSvc["Reporting Service"]
        AuditSvc["Audit Service"]
    end

    subgraph DataLayer["Data Layer"]
        SqliteDb[("SQLite")]
        ChromaDb[("ChromaDB")]
        FileStore[("Document Files")]
    end

    subgraph AiLayer["AI and External Runtime"]
        LangChainFlow["LangChain Orchestration"]
        BedrockProvider["AWS Bedrock Provider"]
    end

    Browser -->|"loads app"| StreamlitUi
    StreamlitUi -->|"auth requests"| AuthApi
    StreamlitUi -->|"admin uploads"| AdminApi
    StreamlitUi -->|"interview actions"| InterviewApi
    StreamlitUi -->|"reports and reviews"| ReportApi

    AuthApi -->|"delegates"| AuthSvc
    AdminApi -->|"delegates"| IngestSvc
    InterviewApi -->|"starts and advances sessions"| Orchestrator
    ReportApi -->|"builds summaries"| ReportSvc

    Orchestrator -->|"evaluate answers"| EvalSvc
    Orchestrator -->|"request probes"| FollowupSvc
    EvalSvc -->|"retrieve context"| RetrievalSvc
    EvalSvc -->|"record evidence trail"| AuditSvc
    ReportSvc -->|"read evaluations"| AuditSvc

    AuthSvc -->|"user and session data"| SqliteDb
    IngestSvc -->|"store metadata"| SqliteDb
    IngestSvc -->|"save raw files"| FileStore
    IngestSvc -->|"index chunks"| ChromaDb
    Orchestrator -->|"session state"| SqliteDb
    EvalSvc -->|"score records"| SqliteDb
    AuditSvc -->|"audit records"| SqliteDb
    RetrievalSvc -->|"vector lookups"| ChromaDb

    EvalSvc -->|"prompt workflow"| LangChainFlow
    FollowupSvc -->|"probe generation"| LangChainFlow
    RetrievalSvc -.->|"context to prompt"| LangChainFlow
    LangChainFlow -->|"model calls"| BedrockProvider
```

### Technology Stack Summary

| Layer | Technology | Version | Purpose |
| --- | --- | --- | --- |
| Client | Streamlit | MVP target | Candidate and admin web experience |
| API | FastAPI | MVP target | Application services and route boundaries |
| Domain Services | Python services | MVP target | Interview orchestration, scoring, ingestion, reporting, and audit logic |
| Transactional Data | SQLite | MVP target | Users, topics, sessions, answers, evaluations, and audit records |
| Retrieval Data | ChromaDB | MVP target | Vector storage for approved contextual reference content |
| AI Orchestration | LangChain v1 | Planned | Prompt orchestration and provider abstraction |
| Model Runtime | AWS Bedrock | Planned | Managed model access through provider abstraction |

### Data Storage and External Services

The MVP uses SQLite as the primary transactional store for users, topics, questions, sessions, answers, evaluations, and audit data. ChromaDB stores vectorized chunks of approved contextual source material used during answer evaluation. Uploaded source files, especially PDFs, are retained in a document file store so ingestion provenance and later review remain possible. LangChain mediates prompt construction and evaluation workflows, while AWS Bedrock provides the underlying model runtime.

### Key Architectural Decisions

- Keep Streamlit thin and route all core business logic through FastAPI-owned services so the UI can be replaced later without rewriting evaluation behavior.
- Separate transactional persistence from retrieval persistence: SQLite owns system records, while ChromaDB owns contextual chunks and vector search.
- Preserve an explicit audit trail for every evaluation decision, including retrieved evidence, thresholds, follow-up usage, and model metadata.

## Component Relationships

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
```mermaid
flowchart LR
    subgraph PresentationLayer["Presentation"]
        cAdminPages["Admin Pages"]
        cCandidatePages["Candidate Pages"]
    end

    subgraph ApplicationLayer["Application"]
        cAuthController["Auth Controller"]
        cAdminController["Admin Controller"]
        cInterviewController["Interview Controller"]
        cReportController["Report Controller"]
    end

    subgraph BusinessLayer["Business Logic"]
        cAuthService["Auth Service"]
        cUploadValidator["Upload Validator"]
        cContentService["Content Service"]
        cInterviewService["Interview Orchestrator"]
        cEvaluationEngine["Evaluation Engine"]
        cFollowupEngine["Followup Engine"]
        cRetrievalEngine["Retrieval Service"]
        cReportService["Report Service"]
        cAuditService["Audit Service"]
    end

    subgraph DataAccessLayer["Data Access"]
        cUserRepo["User Repository"]
        cTopicRepo["Topic Repository"]
        cSessionRepo["Session Repository"]
        cEvalRepo["Evaluation Repository"]
        cVectorRepo["Vector Repository"]
        cFileRepo["File Repository"]
    end

    subgraph InfraLayer["Infrastructure"]
        cPromptRuntime["LangChain Runtime"]
        cModelProvider["Bedrock Provider"]
    end

    cAdminPages -->|"submits admin actions"| cAdminController
    cCandidatePages -->|"submits interview actions"| cInterviewController
    cCandidatePages -->|"sign in"| cAuthController
    cAdminPages -->|"sign in"| cAuthController
    cAdminPages -->|"review reports"| cReportController

    cAuthController -->|"delegates"| cAuthService
    cAdminController -->|"validate upload"| cUploadValidator
    cAdminController -->|"manage content"| cContentService
    cInterviewController -->|"start and advance"| cInterviewService
    cReportController -->|"assemble outputs"| cReportService

    cUploadValidator -->|"approved import"| cContentService
    cInterviewService -->|"score answer"| cEvaluationEngine
    cInterviewService -->|"request followup"| cFollowupEngine
    cEvaluationEngine -->|"needs context"| cRetrievalEngine
    cEvaluationEngine -->|"write audit"| cAuditService
    cFollowupEngine -->|"generate prompt"| cPromptRuntime
    cReportService -->|"read audit and scores"| cAuditService

    cAuthService -->|"read and write"| cUserRepo
    cContentService -->|"topics and questions"| cTopicRepo
    cContentService -->|"save uploads"| cFileRepo
    cContentService -->|"index context"| cVectorRepo
    cInterviewService -->|"session state"| cSessionRepo
    cEvaluationEngine -->|"persist results"| cEvalRepo
    cRetrievalEngine -->|"query vectors"| cVectorRepo
    cAuditService -->|"persist audit"| cEvalRepo

    cEvaluationEngine -->|"invoke model workflow"| cPromptRuntime
    cRetrievalEngine -.->|"supply evidence"| cPromptRuntime
    cPromptRuntime -->|"model invocation"| cModelProvider
```

### Component Inventory

| Component | Layer | Type | Responsibility |
| --- | --- | --- | --- |
| Admin Pages | Presentation | Streamlit pages | Topic setup, uploads, threshold configuration, and report review |
| Candidate Pages | Presentation | Streamlit pages | Login, interview flow, follow-up answers, and feedback display |
| Auth Controller | Application | FastAPI route set | Authentication and session entry points |
| Admin Controller | Application | FastAPI route set | Upload, preview, publish, and content management endpoints |
| Interview Controller | Application | FastAPI route set | Interview session lifecycle and answer submission endpoints |
| Report Controller | Application | FastAPI route set | Session summaries and admin review endpoints |
| Auth Service | Business Logic | Service | Credential validation and role-aware access control |
| Upload Validator | Business Logic | Service | Structured file validation and preview generation |
| Content Service | Business Logic | Service | Topic, question, rubric, and context ingestion orchestration |
| Interview Orchestrator | Business Logic | Service | Session state transitions and branching into evaluation or follow-up |
| Evaluation Engine | Business Logic | Service | Rubric scoring, confidence calculation, and evidence-driven evaluation |
| Followup Engine | Business Logic | Service | Follow-up question generation with max-3 enforcement |
| Retrieval Service | Business Logic | Service | ChromaDB search over approved contextual content |
| Report Service | Business Logic | Service | Candidate summaries and admin review projections |
| Audit Service | Business Logic | Service | Persistence of thresholds, evidence links, model metadata, and evaluation trace |
| User Repository | Data Access | Repository | Users, credentials, and role-related persistence |
| Topic Repository | Data Access | Repository | Topics, questions, contexts, and rubric metadata |
| Session Repository | Data Access | Repository | Interview sessions, answers, and follow-up sequence state |
| Evaluation Repository | Data Access | Repository | Evaluations, audit records, and reporting projections |
| Vector Repository | Data Access | Repository | Context chunk indexing and retrieval lookup |
| File Repository | Data Access | Repository | Raw uploaded file metadata and source file access |
| LangChain Runtime | Infrastructure | Orchestration runtime | Prompt assembly, structured response parsing, and provider abstraction |
| Bedrock Provider | Infrastructure | External runtime adapter | Managed model invocation through AWS Bedrock |