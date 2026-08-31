---
name: test-generation
description: 'Generate focused tests for the AI Interview Tool. Use for unit tests, integration tests, schema validation tests, ingestion validation tests, confidence-branching tests, and auditability checks.'
argument-hint: 'Describe the feature or business rule to test'
user-invocable: true
---

# Test Generation

## When to Use
- Add tests for a new vertical slice
- Validate business rules for ingestion, scoring, follow-up logic, or reporting
- Add schema contract tests for candidate-visible or admin-visible outputs

## Required Context
Read the relevant feature docs first, usually including:
- `docs/product-requirements.md`
- `docs/admin-upload-templates.md`
- `docs/evaluation-response-schemas.md`

## Rules
- Prefer business-rule tests over framework-only smoke tests.
- Add at least one falsifiable test for each new branch or rule.
- Keep test fixtures small and explicit.
- Separate unit tests from integration tests.
- Verify candidate-safe output filtering where feedback is exposed.

## Procedure
1. Identify the exact requirement or schema behavior to validate.
2. Write the narrowest test that can fail if the rule is broken.
3. Add only the fixtures and mocks needed for that rule.
4. Add an integration test when the feature crosses service or persistence boundaries.
5. Document what branch, threshold, or contract the test protects.

## Expected Output
- Focused tests aligned to one business rule or one slice
- Clear fixture setup
- Explicit validation of structured outputs, thresholds, or provenance rules