# Admin Upload Templates

## Purpose
This document defines the admin-managed upload formats for question banks, rubric criteria, contextual reference mappings, and PDF support material used by the AI Interview Tool MVP. These templates support `REQ-005` through `REQ-010` in the product requirements.

## Upload Types in MVP
- CSV question bank import
- Excel question bank import
- JSON bulk import
- PDF reference content upload

## Upload Workflow
1. Admin selects a topic or creates a new topic.
2. Admin uploads one of the supported structured templates.
3. The system validates required fields, formats, and references.
4. The system shows a preview with row-level errors and warnings.
5. Admin confirms import.
6. Imported content remains reviewable before it is published for candidate interviews.

## Canonical Data Concepts
- `topic_code`: Stable identifier for a topic such as `PY_BACKEND_001`
- `question_code`: Stable identifier for a question such as `PY_API_Q01`
- `context_code`: Stable identifier for a context record such as `CTX_FASTAPI_01`
- `criterion_code`: Stable identifier for a rubric criterion such as `CRIT_ACCURACY`
- `weight`: Numeric contribution of a criterion to the total score
- `followup_enabled`: Whether a question may enter the follow-up loop
- `published`: Whether the imported entity is available in candidate interviews

## CSV and Excel Template
CSV and Excel imports should represent one question per row. Excel must use a single worksheet named `questions` for MVP compatibility.

### Required Columns
| Column | Required | Type | Description |
| --- | --- | --- | --- |
| `topic_code` | Yes | String | Unique topic identifier |
| `topic_name` | Yes | String | Display name for the topic |
| `question_code` | Yes | String | Unique question identifier within the topic |
| `question_text` | Yes | String | Interview question shown to the candidate |
| `question_type` | Yes | Enum | `behavioral`, `technical`, `scenario`, `communication` |
| `difficulty` | Yes | Enum | `easy`, `medium`, `hard` |
| `expected_answer_summary` | Yes | String | Short rubric-oriented expected answer summary |
| `followup_enabled` | Yes | Boolean | `true` or `false` |
| `max_followups` | Yes | Integer | Allowed values `0` to `3` |
| `confidence_low` | Yes | Decimal | Lower confidence threshold |
| `confidence_mid_start` | Yes | Decimal | Start of the mid-confidence band |
| `confidence_mid_end` | Yes | Decimal | End of the mid-confidence band |
| `confidence_high` | Yes | Decimal | High-confidence threshold |
| `published` | Yes | Boolean | `true` or `false` |

### Optional Columns
| Column | Type | Description |
| --- | --- | --- |
| `question_prompt_notes` | String | Internal admin notes not shown to candidate |
| `time_limit_seconds` | Integer | Suggested response time |
| `tags` | String | Pipe-delimited tags such as `fastapi|rest|python` |
| `language` | String | Language hint such as `en` |
| `context_codes` | String | Pipe-delimited context references such as `CTX_FASTAPI_01|CTX_HTTP_02` |
| `source_reference` | String | External source or policy reference |

### CSV Example
```csv
topic_code,topic_name,question_code,question_text,question_type,difficulty,expected_answer_summary,followup_enabled,max_followups,confidence_low,confidence_mid_start,confidence_mid_end,confidence_high,published,question_prompt_notes,time_limit_seconds,tags,language,context_codes,source_reference
PY_BACKEND_001,Python Backend Engineer,PY_API_Q01,"How would you design a FastAPI endpoint for idempotent order creation?",technical,medium,"Candidate should explain idempotency key handling, validation, persistence boundaries, and API response behavior.",true,3,0.30,0.40,0.69,0.70,true,"Focus on design tradeoffs rather than framework trivia",180,fastapi|api|backend,en,CTX_FASTAPI_01|CTX_IDEMPOTENCY_02,internal_playbook_v1
```

## Rubric Criteria Template
Rubric criteria may be uploaded as a separate CSV, Excel sheet, or JSON collection keyed by `question_code`.

### Required Columns
| Column | Required | Type | Description |
| --- | --- | --- | --- |
| `question_code` | Yes | String | Parent question identifier |
| `criterion_code` | Yes | String | Stable rubric criterion identifier |
| `criterion_name` | Yes | String | Short criterion label |
| `criterion_description` | Yes | String | What the evaluator should look for |
| `weight` | Yes | Decimal | Weight contribution to total score |
| `min_score` | Yes | Integer | Usually `0` |
| `max_score` | Yes | Integer | Usually `5` or `10` |
| `evidence_required` | Yes | Boolean | Whether grounded evidence is required |

### Rubric Example
```csv
question_code,criterion_code,criterion_name,criterion_description,weight,min_score,max_score,evidence_required
PY_API_Q01,CRIT_ACCURACY,Technical Accuracy,"Explains correct idempotency behavior and duplicate request handling.",0.40,0,5,true
PY_API_Q01,CRIT_STRUCTURE,API Design,"Defines endpoint shape, validation, response codes, and persistence boundary.",0.35,0,5,true
PY_API_Q01,CRIT_COMMUNICATION,Clarity,"Presents a coherent answer with clear sequencing and tradeoffs.",0.25,0,5,false
```

## Context Reference Template
Context records link approved source material to questions or topics. Context can come from manual structured upload or derived chunks from PDFs.

### Required Columns
| Column | Required | Type | Description |
| --- | --- | --- | --- |
| `context_code` | Yes | String | Stable context identifier |
| `scope_type` | Yes | Enum | `topic` or `question` |
| `scope_code` | Yes | String | `topic_code` or `question_code` |
| `context_title` | Yes | String | Friendly label for the source |
| `context_text` | Yes | String | Approved context text or summary |
| `source_type` | Yes | Enum | `manual`, `csv`, `excel`, `json`, `pdf` |
| `published` | Yes | Boolean | Whether usable at runtime |

### Optional Columns
| Column | Type | Description |
| --- | --- | --- |
| `page_reference` | String | Page range for PDF content |
| `section_reference` | String | Logical heading or section label |
| `priority` | Integer | Retrieval ordering hint |
| `notes` | String | Internal admin notes |

## JSON Bulk Import Template
JSON bulk import supports importing a complete topic package in one file.

### JSON Structure
```json
{
  "topic": {
    "topic_code": "PY_BACKEND_001",
    "topic_name": "Python Backend Engineer",
    "description": "Interview set for Python backend and API design",
    "published": false
  },
  "questions": [
    {
      "question_code": "PY_API_Q01",
      "question_text": "How would you design a FastAPI endpoint for idempotent order creation?",
      "question_type": "technical",
      "difficulty": "medium",
      "expected_answer_summary": "Candidate should explain idempotency key handling, validation, persistence boundaries, and response behavior.",
      "followup_enabled": true,
      "max_followups": 3,
      "confidence_thresholds": {
        "low": 0.30,
        "mid_start": 0.40,
        "mid_end": 0.69,
        "high": 0.70
      },
      "tags": ["fastapi", "api", "backend"],
      "context_codes": ["CTX_FASTAPI_01", "CTX_IDEMPOTENCY_02"],
      "rubric": [
        {
          "criterion_code": "CRIT_ACCURACY",
          "criterion_name": "Technical Accuracy",
          "criterion_description": "Explains correct idempotency behavior and duplicate request handling.",
          "weight": 0.40,
          "min_score": 0,
          "max_score": 5,
          "evidence_required": true
        }
      ]
    }
  ],
  "contexts": [
    {
      "context_code": "CTX_FASTAPI_01",
      "scope_type": "question",
      "scope_code": "PY_API_Q01",
      "context_title": "FastAPI request lifecycle summary",
      "context_text": "Idempotent create flows should separate validation, duplicate detection, and persistence steps.",
      "source_type": "manual",
      "published": true
    }
  ]
}
```

## PDF Upload Template and Metadata
PDF uploads do not require tabular content, but the admin workflow should capture metadata at upload time.

### Required Metadata
| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `topic_code` | Yes | String | Owning topic |
| `document_title` | Yes | String | Friendly document label |
| `document_type` | Yes | Enum | `reference`, `policy`, `guide`, `sample_answer_basis` |
| `scope_type` | Yes | Enum | `topic` or `question` |
| `scope_code` | Yes | String | Topic or question identifier |
| `published` | Yes | Boolean | Whether retrieval may use the processed chunks |

### PDF Processing Expectations
- Extract text and preserve page references where possible.
- Chunk text into retrieval-ready segments.
- Attach each chunk to the owning `topic_code` or `question_code`.
- Store provenance including source filename, page number, chunk identifier, and upload timestamp.
- Keep PDF-derived content reviewable before it is active for candidate evaluation.

## Validation Rules
- `topic_code`, `question_code`, `context_code`, and `criterion_code` must be unique within their scope.
- `max_followups` must be between `0` and `3`.
- Thresholds must satisfy `confidence_low <= confidence_mid_start <= confidence_mid_end <= confidence_high`.
- Rubric weights for a question must sum to `1.0` or `100`, depending on implementation choice. The system should normalize only if that behavior is explicitly documented.
- Every `context_code` referenced by a question must exist in the import batch or already exist in the selected topic.
- Every `question_code` referenced by a rubric row must exist.
- Boolean fields must accept only explicit boolean values, not free-form text.
- Empty required values must block publish and show row-level errors.

## Error Reporting Requirements
- Validation must return row number, field name, severity, and a human-readable message.
- Imports may proceed only after blocking errors are resolved.
- Warnings may be allowed for missing optional metadata but must be visible in preview.

## Recommended File Names
- `questions.csv`
- `questions.xlsx`
- `rubric.csv`
- `context.csv`
- `topic-package.json`
- `reference-guide.pdf`

## Implementation Notes
- Use a canonical internal import model regardless of input format.
- Keep preview parsing deterministic so the same input produces the same validation result.
- Separate import validation from publish activation.