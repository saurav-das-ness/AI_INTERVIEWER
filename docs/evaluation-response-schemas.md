# Evaluation Response Schemas

## Purpose
This document defines the structured response payloads for answer evaluation, follow-up generation, rescoring, and session summaries in the AI Interview Tool MVP. These schemas support `REQ-015` through `REQ-031` and should be treated as the contract for service-to-service and API responses.

## Design Principles
- Evaluation responses must be structured and schema-validated.
- Responses must be auditable and preserve evidence references.
- Responses must separate candidate-visible feedback from internal scoring metadata.
- The ideal answer must never be exposed in candidate-visible fields during the active interview.

## Common Field Definitions
| Field | Type | Description |
| --- | --- | --- |
| `session_id` | String | Unique interview session identifier |
| `question_code` | String | Question identifier |
| `answer_id` | String | Unique answer record identifier |
| `evaluation_id` | String | Unique evaluation record identifier |
| `timestamp_utc` | String | ISO 8601 timestamp |
| `confidence_score` | Decimal | Numeric confidence value from `0.0` to `1.0` |
| `confidence_band` | Enum | `low`, `mid`, `high` |
| `finalize_decision` | Enum | `finalize`, `followup_required`, `manual_review` |

## Primary Answer Evaluation Schema
This schema represents the result of evaluating a candidate's initial answer.

### JSON Shape
```json
{
  "session_id": "SES_20260814_001",
  "question_code": "PY_API_Q01",
  "answer_id": "ANS_0001",
  "evaluation_id": "EVAL_0001",
  "timestamp_utc": "2026-08-14T10:15:30Z",
  "score": {
    "raw_score": 3.8,
    "max_score": 5.0,
    "normalized_score": 0.76,
    "percentage": 76.0
  },
  "criteria_results": [
    {
      "criterion_code": "CRIT_ACCURACY",
      "criterion_name": "Technical Accuracy",
      "weight": 0.40,
      "score_awarded": 4.0,
      "max_score": 5.0,
      "reasoning": "The answer correctly explained idempotency keys and duplicate request handling.",
      "evidence_used": ["EV_001", "EV_002"],
      "missing_signals": ["Did not describe persistence race conditions"]
    },
    {
      "criterion_code": "CRIT_STRUCTURE",
      "criterion_name": "API Design",
      "weight": 0.35,
      "score_awarded": 3.5,
      "max_score": 5.0,
      "reasoning": "The answer covered endpoint flow but lacked response-code detail.",
      "evidence_used": ["EV_001"],
      "missing_signals": ["No explicit HTTP status handling"]
    }
  ],
  "feedback": {
    "strengths": [
      "Explained the purpose of idempotency keys clearly",
      "Connected validation and duplicate detection logically"
    ],
    "gaps": [
      "Did not explain failure-path response codes",
      "Did not mention concurrent request safeguards"
    ],
    "candidate_visible_summary": "Good core design explanation, but the answer needs more detail on response handling and concurrency protection."
  },
  "evidence_references": [
    {
      "evidence_id": "EV_001",
      "context_code": "CTX_FASTAPI_01",
      "source_type": "manual",
      "source_label": "FastAPI request lifecycle summary",
      "excerpt": "Idempotent create flows should separate validation, duplicate detection, and persistence steps.",
      "page_reference": null,
      "relevance_score": 0.92
    }
  ],
  "confidence": {
    "confidence_score": 0.58,
    "confidence_band": "mid",
    "rationale": "The answer covered core concepts but omitted enough implementation detail to justify probing."
  },
  "decision": {
    "finalize_decision": "followup_required",
    "followup_count_allowed": 3,
    "followup_count_used": 0
  },
  "model_metadata": {
    "provider": "bedrock",
    "model_name": "anthropic.claude-sonnet",
    "prompt_version": "eval_v1",
    "temperature": 0.1
  },
  "audit": {
    "thresholds_applied": {
      "low": 0.30,
      "mid_start": 0.40,
      "mid_end": 0.69,
      "high": 0.70
    },
    "grounding_scope": "question-linked",
    "evaluation_mode": "initial"
  }
}
```

## Follow-Up Question Generation Schema
This schema is returned when the answer requires more evidence before final scoring.

```json
{
  "session_id": "SES_20260814_001",
  "question_code": "PY_API_Q01",
  "answer_id": "ANS_0001",
  "evaluation_id": "EVAL_0001",
  "followup_required": true,
  "followup_sequence": 1,
  "max_followups": 3,
  "followup_question": {
    "followup_id": "FU_0001",
    "prompt": "How would you prevent duplicate order creation when two identical requests arrive at nearly the same time?",
    "purpose": "Probe concurrency safeguards and persistence strategy",
    "linked_criteria": ["CRIT_ACCURACY", "CRIT_STRUCTURE"]
  },
  "candidate_visible_guidance": "Please provide a bit more detail so the system can assess your implementation approach more accurately."
}
```

## Follow-Up Answer Capture Schema
This schema represents the persisted result after the candidate answers a follow-up question.

```json
{
  "session_id": "SES_20260814_001",
  "question_code": "PY_API_Q01",
  "answer_id": "ANS_0001",
  "followup_id": "FU_0001",
  "followup_answer_id": "FUA_0001",
  "followup_sequence": 1,
  "candidate_response": "I would store the idempotency key with a uniqueness constraint and treat duplicates as replay responses.",
  "timestamp_utc": "2026-08-14T10:17:12Z"
}
```

## Rescored Evaluation Schema
This schema represents the final evaluation after one or more follow-up answers are incorporated.

```json
{
  "session_id": "SES_20260814_001",
  "question_code": "PY_API_Q01",
  "answer_id": "ANS_0001",
  "evaluation_id": "EVAL_0002",
  "replaces_evaluation_id": "EVAL_0001",
  "timestamp_utc": "2026-08-14T10:17:20Z",
  "score": {
    "raw_score": 4.3,
    "max_score": 5.0,
    "normalized_score": 0.86,
    "percentage": 86.0
  },
  "confidence": {
    "confidence_score": 0.81,
    "confidence_band": "high",
    "rationale": "The follow-up clarified persistence and concurrency safeguards."
  },
  "decision": {
    "finalize_decision": "finalize",
    "followup_count_allowed": 3,
    "followup_count_used": 1
  },
  "feedback": {
    "strengths": [
      "Clarified how uniqueness constraints prevent duplicate creation",
      "Improved explanation of replay behavior for repeated requests"
    ],
    "gaps": [
      "Could still be more explicit about response-body consistency"
    ],
    "candidate_visible_summary": "Your follow-up improved the answer by clarifying concurrency and persistence safeguards."
  },
  "followup_trace": [
    {
      "followup_id": "FU_0001",
      "followup_sequence": 1,
      "prompt": "How would you prevent duplicate order creation when two identical requests arrive at nearly the same time?",
      "response_id": "FUA_0001"
    }
  ],
  "audit": {
    "grounding_scope": "question-linked",
    "evaluation_mode": "rescored",
    "previous_evaluation_retained": true
  }
}
```

## Candidate-Facing Answer Result Schema
This schema contains only the subset of fields safe to expose directly to the candidate after an answer is finalized.

```json
{
  "session_id": "SES_20260814_001",
  "question_code": "PY_API_Q01",
  "answer_id": "ANS_0001",
  "score_percentage": 86.0,
  "confidence_band": "high",
  "strengths": [
    "You explained idempotency handling clearly",
    "You improved the answer by addressing concurrency controls"
  ],
  "gaps": [
    "You can further improve by describing response consistency in more detail"
  ],
  "summary": "Strong answer with clear idempotency reasoning and better follow-up detail on concurrency safeguards."
}
```

## Admin Review Schema
This schema supports admin-side review of how a score was produced.

```json
{
  "session_id": "SES_20260814_001",
  "question_code": "PY_API_Q01",
  "candidate_id": "USR_0100",
  "answer_id": "ANS_0001",
  "initial_evaluation_id": "EVAL_0001",
  "final_evaluation_id": "EVAL_0002",
  "status": "finalized",
  "score_percentage": 86.0,
  "confidence_band": "high",
  "evidence_references": [
    {
      "evidence_id": "EV_001",
      "context_code": "CTX_FASTAPI_01",
      "source_label": "FastAPI request lifecycle summary"
    }
  ],
  "thresholds_applied": {
    "low": 0.30,
    "mid_start": 0.40,
    "mid_end": 0.69,
    "high": 0.70
  },
  "followups_used": 1,
  "model_metadata": {
    "provider": "bedrock",
    "model_name": "anthropic.claude-sonnet",
    "prompt_version": "eval_v1"
  }
}
```

## Session Summary Schema
This schema supports end-of-interview reporting.

```json
{
  "session_id": "SES_20260814_001",
  "candidate_id": "USR_0100",
  "topic_code": "PY_BACKEND_001",
  "started_at_utc": "2026-08-14T10:00:00Z",
  "completed_at_utc": "2026-08-14T10:25:00Z",
  "question_count": 5,
  "average_score_percentage": 78.4,
  "overall_strengths": [
    "Explains backend design clearly",
    "Responds well to probing questions"
  ],
  "overall_gaps": [
    "Needs more precise discussion of operational edge cases"
  ],
  "answers": [
    {
      "question_code": "PY_API_Q01",
      "score_percentage": 86.0,
      "confidence_band": "high",
      "followups_used": 1
    }
  ]
}
```

## Validation Rules
- `confidence_score` must be between `0.0` and `1.0`.
- `confidence_band` must align with the configured thresholds used at evaluation time.
- `followup_count_used` must never exceed `followup_count_allowed`.
- Candidate-visible payloads must exclude internal reasoning that leaks the ideal answer.
- Evidence references must point only to approved topic-linked or question-linked context.
- Rescored evaluations must retain a link to the initial evaluation.
- Every stored evaluation must include model metadata and threshold metadata for audit review.

## Recommended Implementation Notes
- Keep separate schemas for internal evaluation, admin review, and candidate-visible results.
- Version these schemas once APIs are exposed externally.
- Favor Pydantic or equivalent typed schema validation for all response objects.