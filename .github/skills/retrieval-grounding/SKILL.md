---
name: retrieval-grounding
description: 'Implement context chunking, indexing, retrieval, and evidence linking for the AI Interview Tool. Use for ChromaDB integration, PDF-derived context, question-linked grounding, and evidence traceability.'
argument-hint: 'Describe the retrieval or grounding slice to implement'
user-invocable: true
---

# Retrieval Grounding

## When to Use
- Add ChromaDB indexing for approved context
- Implement retrieval for answer evaluation
- Link PDF-derived chunks back to topic and question records
- Return evidence references for admin review and audit trails

## Required Context
Read these documents before implementation:
- `docs/application-architecture.md`
- `docs/admin-upload-templates.md`
- `docs/evaluation-response-schemas.md`
- `docs/entity-relationship-diagram.md`

## Rules
- Use ChromaDB only for retrieval-oriented context records and embeddings.
- Keep SQLite or the transactional store as the system of record.
- Only retrieve approved topic-linked or question-linked context.
- Return enough metadata to trace each evidence snippet back to its source.
- Keep provider and vector logic outside UI code.

## Procedure
1. Define the chunk metadata contract from the context and entity docs.
2. Implement chunking, indexing, and source linkage for uploaded context.
3. Implement scoped retrieval by topic or question.
4. Return evidence references suitable for evaluation and audit payloads.
5. Add tests for scope filtering, missing context behavior, and provenance retention.

## Expected Output
- Indexing and retrieval services
- Metadata contract for chunk provenance
- Scoped evidence responses for evaluation flows
- Focused tests for grounding behavior