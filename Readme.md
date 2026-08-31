# AI Role Play Interviewing Tool

Text-first AI-assisted interview practice. Admins upload question banks and supporting context; candidates answer questions that are scored against weighted rubrics and grounded evidence, with adaptive follow-up probing when confidence is uncertain.

## Getting Started

### Prerequisites
- Python 3.11+
- No AWS account required for local development — the app automatically falls back to deterministic local embeddings and feedback generation when Bedrock credentials aren't configured.

### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest  # only needed to run the test suite
```

### Run the Streamlit app
```bash
source .venv/bin/activate
streamlit run streamlit_app/Home.py
```
Then open http://localhost:8501. On first use, register an account from the Home page (choose the `admin` role to manage content, `candidate` to take interviews), then:
1. **Home** — register/login.
2. **Admin** — upload a JSON/CSV/Excel question bank or a PDF for context, then publish the topic.
3. **Interview** — as a candidate, pick a published topic and answer questions.
4. **Reports** — view scored session summaries (candidates see their own; admins see everyone's plus full evaluation detail).

Data is stored locally under `storage/` (SQLite DB, ChromaDB vector store, uploaded files) — safe to delete for a clean slate.

### Run the FastAPI service (optional)
The Streamlit UI calls the service layer directly, so this isn't required to use the app, but the same business logic is also exposed over HTTP:
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

### Run tests
```bash
source .venv/bin/activate
python -m pytest tests -q
```

### Configuration
All settings have local-friendly defaults (`app/core/settings.py`) and can be overridden with environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AI_INTERVIEW_SQLITE_DB` | `storage/app.db` | SQLite database path |
| `AI_INTERVIEW_CHROMA_DIR` | `storage/chroma` | ChromaDB persistence directory |
| `AI_INTERVIEW_CHROMA_COLLECTION` | `ai_interview_context` | ChromaDB collection name |
| `AI_INTERVIEW_UPLOADS_DIR` | `storage/uploads` | Raw uploaded file storage |
| `AI_INTERVIEW_PROVIDER_MODE` | `bedrock` | Set to anything else to force the local fallback provider |
| `AWS_REGION` / `AWS_DEFAULT_REGION` | unset | Enables Bedrock embeddings/feedback when valid AWS credentials are also present |
| `AI_INTERVIEW_BEDROCK_MODEL_ID` | `anthropic.claude-3-5-sonnet-20240620-v1:0` | Bedrock feedback model |
| `AI_INTERVIEW_BEDROCK_EMBED_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Bedrock embedding model |

## Architecture
- **FastAPI** (`app/`) owns the domain logic: auth, content ingestion, interview orchestration, evaluation, retrieval, and reporting.
- **Streamlit** (`streamlit_app/`) is the MVP UI and calls the service layer directly.
- **SQLite** stores transactional data (users, topics, questions, sessions, answers, evaluations).
- **ChromaDB** stores question-linked context for retrieval-grounded evaluation.
- **AWS Bedrock** (via LangChain) generates qualitative feedback and embeddings when configured; otherwise a deterministic local fallback keeps the app fully usable offline.

## Scope
- Included: text interviewing, admin-managed question banks, context-grounded scoring, adaptive follow-ups (up to 3 per question), saved reports, email/password login.
- Deferred: voice, video/avatar simulation, enterprise SSO.
- This is an interview-readiness evaluation tool, not a hiring-decision engine.
