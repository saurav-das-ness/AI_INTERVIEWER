---
name: evaluation-engine
description: 'Implement answer scoring, confidence calculation, follow-up triggering, rescoring, and candidate-safe feedback for the AI Interview Tool. Use for rubric-based evaluation, structured response schemas, and audit-friendly scoring logic.'
argument-hint: 'Describe the evaluation behavior or schema slice to implement'
user-invocable: true
---

# Evaluation Engine

## When to Use
- Build initial answer scoring
- Implement confidence-band decisions and follow-up triggering
- Generate rescored outputs after follow-up answers
- Add candidate-visible and admin-visible evaluation projections

## Required Context
Read these documents before implementation:
- `docs/product-requirements.md`
- `docs/evaluation-response-schemas.md`
- `docs/entity-relationship-diagram.md`

## Rules
- Evaluate answers against rubric criteria, weights, and approved retrieved context.
- Keep outputs schema-validated and structured.
- Preserve both initial and rescored evaluations.
- Never expose the ideal answer during the active interview flow.
- Enforce the maximum of 3 follow-up questions.
- Record evidence references, thresholds, and model metadata for audit review.

## Procedure
1. Implement domain models or schemas that match the evaluation response document.
2. Build scoring logic first, then confidence branching, then follow-up generation.
3. Separate internal evaluation payloads from candidate-safe payloads.
4. Persist initial evaluation before triggering a follow-up branch.
5. Add tests for threshold branching, follow-up count limits, rescoring, and candidate-safe filtering.

## Expected Output
- Evaluation service logic aligned with the response schemas
- Follow-up and rescoring flow where required
- Audit-friendly persistence points
- Focused tests for the implemented branch logic