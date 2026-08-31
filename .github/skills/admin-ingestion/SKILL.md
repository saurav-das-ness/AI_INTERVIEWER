---
name: admin-ingestion
description: 'Implement admin upload, validation, preview, and publish workflows for the AI Interview Tool. Use for CSV, Excel, JSON, and PDF ingestion, provenance tracking, rubric import, and context linking.'
argument-hint: 'Describe the ingestion flow or upload type to implement'
user-invocable: true
---

# Admin Ingestion

## When to Use
- Build admin upload flows for question banks, rubrics, contexts, or PDFs
- Add validation rules, preview behavior, provenance storage, or publish controls
- Convert upload templates into internal models and persistence records

## Required Context
Read these documents before implementation:
- `docs/product-requirements.md`
- `docs/admin-upload-templates.md`
- `docs/entity-relationship-diagram.md`

## Rules
- Treat ingestion as `validate -> preview -> persist -> publish`.
- Do not activate imported content immediately after upload.
- Preserve provenance for every imported question, rubric, context, and document.
- Keep upload parsing deterministic so the same file produces the same validation result.
- Route ingestion logic through services, not Streamlit pages.

## Procedure
1. Identify the upload type and the canonical internal model it maps to.
2. Implement row-level or object-level validation from the upload template doc.
3. Return preview results with blocking errors and warnings.
4. Persist only validated records and store raw file metadata for traceability.
5. Add tests for required fields, reference integrity, threshold constraints, and boolean parsing.

## Expected Output
- Parser and validator for the requested upload type
- Preview response shape or service result
- Persistence and provenance handling
- Focused tests for the specific validation rules implemented