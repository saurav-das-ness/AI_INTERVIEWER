"""LangChain-based feedback provider backed by AWS Bedrock with a local fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import boto3
from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.models.domain.content import Question

logger = logging.getLogger(__name__)


class FeedbackPayload(BaseModel):
    """Structured qualitative feedback generated for an answer evaluation."""

    # Concepts the LLM extracted from the reference chunks as required by a complete answer.
    # Stored for audit transparency; not shown to the candidate.
    expected_concepts: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    candidate_visible_summary: str
    followup_prompt: str | None = None
    followup_purpose: str | None = None
    llm_score: float | None = Field(default=None, ge=0.0, le=1.0)
    llm_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


@dataclass(slots=True)
class FeedbackGenerationResult:
    """Provider output plus provider metadata for audit storage."""

    payload: FeedbackPayload
    provider: str
    model_name: str
    prompt_version: str
    # False when the LLM was unavailable and the local heuristic was used instead.
    llm_used: bool = True


_SYSTEM_PROMPT = (
    "You are a senior technical interviewer grading a candidate's written answer.\n"
    "Your job is to determine whether the candidate UNDERSTANDS the topic, not whether they "
    "can recall keywords related to it.\n\n"
    "═══════════════════════════════════════════════════════════════\n"
    "WHAT \"DEMONSTRATED\" MEANS\n"
    "═══════════════════════════════════════════════════════════════\n"
    "A concept is DEMONSTRATED only when the candidate:\n"
    "  (a) explains the mechanism, principle, or reason — not just names it, and\n"
    "  (b) uses it in a way that would make sense to someone who had never heard the term.\n\n"
    "A concept is NOT demonstrated when the candidate:\n"
    "  • lists the term or its synonyms without any explanation\n"
    "  • strings together domain vocabulary without connecting ideas causally or functionally\n"
    "  • copies phrases from the question or writes generic filler\n"
    "  • provides a definition that is technically true but unrelated to the question asked\n\n"
    "═══════════════════════════════════════════════════════════════\n"
    "ANTI-GAMING CHECKS — apply these before scoring\n"
    "═══════════════════════════════════════════════════════════════\n"
    "KEYWORD STUFFING: The answer loads related terms, buzzwords, or acronyms without "
    "explaining any of them. Test: remove all nouns from the answer — does anything "
    "explanatory remain? If no → stuffing → llm_score ≤ 0.15.\n\n"
    "WORD SALAD: The answer uses correct vocabulary but the sentences do not connect ideas "
    "causally or mechanistically. Test: can you trace a logical chain from the question to "
    "the answer? If not → word salad → llm_score ≤ 0.20.\n\n"
    "TANGENT ANSWER: The answer is coherent but addresses a different question. "
    "Test: does the answer directly address what was asked? If not → llm_score ≤ 0.10.\n\n"
    "QUESTION-AS-ANSWER: The answer copies or restates the question — applies to BOTH the "
    "primary answer AND any follow-up answer. "
    "→ llm_score = 0.0, llm_confidence = 0.0, followup_prompt = null, "
    "expected_concepts = [], strengths = [], gaps = ['Answer must address the question, not repeat it']. "
    "Do NOT perform any further analysis. Finalize immediately.\n\n"
    "VAGUE / BLANK: The answer is too short or contains no real content. "
    "→ llm_score = 0.0, llm_confidence = 0.1, followup_prompt = null. Finalize immediately.\n\n"
    "═══════════════════════════════════════════════════════════════\n"
    "SCORING SCALE\n"
    "═══════════════════════════════════════════════════════════════\n"
    "0.00       Blank, question copy, or pure keyword dump with no explanation\n"
    "0.10-0.25  Names some concepts, explains none; mostly vocabulary without meaning\n"
    "0.26-0.45  Explains 1-2 concepts partially; rest are mentioned only or missing\n"
    "0.46-0.65  Explains several concepts with reasonable depth; some gaps remain\n"
    "0.66-0.85  Explains most required concepts clearly; minor gaps or imprecision\n"
    "0.86-1.00  Explains all required concepts accurately and completely\n\n"
    "═══════════════════════════════════════════════════════════════\n"
    "EVALUATION PROCESS\n"
    "═══════════════════════════════════════════════════════════════\n"
    "1. Read the REFERENCE CHUNKS. They define every concept a correct answer must cover. "
    "Do NOT use general knowledge — chunks are the sole source of truth.\n"
    "2. Derive expected_concepts from the chunks (one short phrase per concept).\n"
    "3. Run all anti-gaming checks. If one fires, cap the score and stop further analysis.\n"
    "4. For each expected concept, apply the DEMONSTRATED test. Score only concepts that pass.\n"
    "5. llm_score = demonstrated_count / total_concepts.\n"
    "6. llm_confidence = your certainty (lower when chunks are sparse or answer is ambiguous).\n\n"
    "═══════════════════════════════════════════════════════════════\n"
    "OUTPUT FIELD RULES\n"
    "═══════════════════════════════════════════════════════════════\n"
    "expected_concepts : concepts extracted from chunks (audit only, not shown to candidate).\n"
    "strengths         : concepts the candidate genuinely explained (specific, not generic).\n"
    "gaps              : required concepts that were missing, named-only, or explained shallowly.\n"
    "candidate_visible_summary:\n"
    "  Write 2-3 honest sentences. Never reveal the ideal answer.\n"
    "  high → acknowledge what was well explained; note minor gaps lightly.\n"
    "  mid  → name what was partially explained and what needs more depth.\n"
    "  low  → state clearly that the answer did not demonstrate sufficient understanding.\n"
    "  If keyword stuffing or word salad was detected, say so plainly without being harsh.\n"
    "followup_prompt : ONE open-ended question about the most important unexplained concept. "
    "Null if the answer was vague, copied, stuffed, or confidence is already high or low. "
    "Null if ANY part (primary or follow-up) was a question copy.\n"
    "followup_purpose: internal note on why that concept matters (not shown to candidate).\n"
    "llm_score       : float 0.0-1.0.\n"
    "llm_confidence  : float 0.0-1.0."
)

_HUMAN_PROMPT = (
    "═══════════════════════════════════════════════════════════════\n"
    "QUESTION BEING ASKED\n"
    "═══════════════════════════════════════════════════════════════\n"
    "Code      : {question_code}\n"
    "Text      : {question_text}\n"
    "Type      : {question_type}  |  Difficulty: {difficulty}\n\n"
    "═══════════════════════════════════════════════════════════════\n"
    "REFERENCE CHUNKS  (ground truth — defines what a correct answer looks like)\n"
    "═══════════════════════════════════════════════════════════════\n"
    "{reference_context}\n\n"
    "═══════════════════════════════════════════════════════════════\n"
    "RUBRIC CRITERIA  (apply these to BOTH the primary answer and any follow-up)\n"
    "═══════════════════════════════════════════════════════════════\n"
    "{criteria_payload}\n\n"
    "═══════════════════════════════════════════════════════════════\n"
    "PRIMARY ANSWER  (check this first against the question text above)\n"
    "═══════════════════════════════════════════════════════════════\n"
    "{answer_text}\n\n"
    "{followup_context}"
    "═══════════════════════════════════════════════════════════════\n"
    "EVALUATION CONTEXT\n"
    "═══════════════════════════════════════════════════════════════\n"
    "Heuristic band      : {confidence_band}\n"
    "Follow-up eligible  : {followup_required}\n\n"
    "═══════════════════════════════════════════════════════════════\n"
    "YOUR EVALUATION STEPS\n"
    "═══════════════════════════════════════════════════════════════\n"
    "Step 1 — QUESTION-COPY CHECK  (run before anything else, on every answer part)\n"
    "  Compare each answer text below against the QUESTION TEXT above.\n"
    "  If the primary answer OR any follow-up answer is the same as, paraphrases, or copies\n"
    "  the question text: apply QUESTION-AS-ANSWER override immediately and stop.\n"
    "  Result: llm_score=0.0, llm_confidence=0.0, followup_prompt=null, finalize.\n\n"
    "Step 2 — CHARACTERISE THE COMBINED ANSWER\n"
    "  (a) KEYWORD DUMP: terms listed without explanation → cap llm_score ≤ 0.15.\n"
    "  (b) WORD SALAD: vocabulary used but ideas not connected → cap llm_score ≤ 0.20.\n"
    "  (c) TANGENT: coherent but wrong question addressed → cap llm_score ≤ 0.10.\n"
    "  (d) GENUINE ATTEMPT: candidate explains concepts → proceed to scoring.\n\n"
    "Step 3 — DERIVE EXPECTED CONCEPTS\n"
    "  From the reference chunks ONLY, extract every concept a complete answer must cover.\n"
    "  Write them as short phrases in expected_concepts.\n\n"
    "Step 4 — SCORE EACH CONCEPT (type (d) answers only)\n"
    "  Evaluate the combined content of PRIMARY + FOLLOW-UP answers together against each concept.\n"
    "  A concept is demonstrated only when EXPLAINED (mechanism, reason, or effect).\n"
    "  Apply all rubric criteria to the combined answer the same way you would to a primary-only answer.\n"
    "  Record as: demonstrated / named-only / missing.\n\n"
    "Step 5 — COMPUTE\n"
    "  llm_score      = demonstrated_count / total_concepts\n"
    "  llm_confidence = certainty (reduce when chunks are sparse or answer is ambiguous)\n\n"
    "Step 6 — POPULATE FEEDBACK\n"
    "  strengths → demonstrated concepts only.\n"
    "  gaps      → named-only and missing concepts.\n\n"
    "Step 7 — WRITE candidate_visible_summary (match confidence band guidance).\n\n"
    "Step 8 — FOLLOW-UP\n"
    "  Eligible only for type (d) answers with mid confidence where no part was a question copy.\n"
    "  Write ONE specific question about the most important unexplained concept.\n"
    "  Set followup_prompt = null in all other cases."
)


def _format_followup_answers(followup_texts: list[str] | None) -> str:
    """Render follow-up answers as a clearly labelled separate section, or empty string."""
    if not followup_texts:
        return ""
    lines = [
        "═══════════════════════════════════════════════════════════════\n"
        "FOLLOW-UP ANSWER(S)  (check each independently against the question text above)\n"
        "═══════════════════════════════════════════════════════════════\n"
    ]
    for i, text in enumerate(followup_texts, start=1):
        lines.append(f"[Follow-up {i}]\n{text or '(no answer provided)'}")
    return "\n\n".join(lines) + "\n\n"


def _format_reference_chunks(evidence_references: list[dict[str, object]]) -> str:
    """Render chunks with source label and relevance score for clear LLM consumption."""
    if not evidence_references:
        return "No reference material was retrieved for this question."
    parts = []
    for i, e in enumerate(evidence_references, start=1):
        source = e.get("context_code") or e.get("source_label") or "unknown"
        relevance = float(e.get("relevance_score", 0.0))
        excerpt = str(e.get("excerpt", "")).strip()
        if excerpt:
            parts.append(f"[Chunk {i} | source: {source} | relevance: {relevance:.2f}]\n{excerpt}")
    return "\n\n".join(parts) if parts else "No reference material was retrieved for this question."


def _format_criteria(criteria_results: list[dict[str, object]]) -> str:
    """Render rubric criteria as a numbered list with descriptions for the LLM to assess against."""
    if not criteria_results:
        return "No rubric criteria configured."
    lines = []
    for i, item in enumerate(criteria_results, start=1):
        name = item.get("criterion_name", "unnamed")
        desc = item.get("criterion_description", "")
        weight = item.get("weight", 0)
        max_score = item.get("max_score", 1)
        line = f"{i}. {name}  (weight: {weight}, max score: {max_score})"
        if desc:
            line += f"\n   What to assess: {desc}"
        lines.append(line)
    return "\n".join(lines)


class FeedbackProvider:
    """Generate qualitative feedback and follow-up prompts behind a provider abstraction."""

    def generate_feedback(
        self,
        *,
        question: Question,
        answer_text: str,
        followup_texts: list[str] | None = None,
        criteria_results: list[dict[str, object]],
        evidence_references: list[dict[str, object]],
        confidence_band: str,
        followup_required: bool,
    ) -> FeedbackGenerationResult:
        raise NotImplementedError


class LocalFeedbackProvider(FeedbackProvider):
    """Deterministic fallback that simulates LLM scoring via text overlap — for tests and local dev."""

    def generate_feedback(
        self,
        *,
        question: Question,
        answer_text: str,
        followup_texts: list[str] | None = None,
        criteria_results: list[dict[str, object]],
        evidence_references: list[dict[str, object]],
        confidence_band: str,
        followup_required: bool,
    ) -> FeedbackGenerationResult:
        import re
        _tok = lambda t: {w.lower() for w in re.findall(r"[a-zA-Z0-9_]{3,}", t)}

        combined = answer_text + (" " + " ".join(followup_texts) if followup_texts else "")
        answer_tokens = _tok(combined)
        scored: list[float] = []
        strengths: list[str] = []
        gaps: list[str] = []

        for item in criteria_results:
            desc = str(item.get("criterion_description", item.get("criterion_name", "")))
            name = str(item.get("criterion_name", "criterion"))
            desc_tokens = _tok(desc)
            ratio = len(answer_tokens & desc_tokens) / len(desc_tokens) if desc_tokens else 0.0
            scored.append(ratio)
            if ratio >= 0.5:
                strengths.append(f"Addressed {name.lower()}")
            else:
                gaps.append(f"Needs more depth on {name.lower()}")

        coverage_ratio = sum(scored) / len(scored) if scored else 0.0
        if coverage_ratio >= 0.75:
            summary = f"Strong answer for {question.question_code} with solid coverage across the main criteria."
        elif coverage_ratio >= 0.5:
            summary = f"Promising answer for {question.question_code}, but some required concepts need more depth."
        else:
            summary = f"The answer for {question.question_code} needs stronger coverage of the required concepts."

        followup_prompt = None
        followup_purpose = None
        if followup_required and gaps:
            focus = gaps[0].replace("Needs more depth on ", "")
            followup_prompt = f"Can you explain {focus} in more detail - what it means and how it works in practice?"
            followup_purpose = f"Probe conceptual depth on {focus}"

        return FeedbackGenerationResult(
            payload=FeedbackPayload(
                strengths=strengths or ["Captured some relevant concepts"],
                gaps=gaps or ["Minor improvement areas only"],
                candidate_visible_summary=summary,
                followup_prompt=followup_prompt,
                followup_purpose=followup_purpose,
                llm_score=round(coverage_ratio, 4),
                llm_confidence=round(coverage_ratio, 4),
            ),
            provider="local-fallback",
            model_name="heuristic-feedback",
            prompt_version="local_v3",
            llm_used=False,
        )


class BedrockFeedbackProvider(FeedbackProvider):
    """Generate structured qualitative feedback with LangChain and Bedrock."""

    def __init__(self, *, region_name: str, model_id: str) -> None:
        self._region_name = region_name
        self._model_id = model_id
        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _SYSTEM_PROMPT),
                ("human", _HUMAN_PROMPT),
            ]
        )
        self._structured_model = ChatBedrockConverse(
            model=self._model_id,
            region_name=self._region_name,
            temperature=0,
        ).with_structured_output(FeedbackPayload)

    def generate_feedback(
        self,
        *,
        question: Question,
        answer_text: str,
        followup_texts: list[str] | None = None,
        criteria_results: list[dict[str, object]],
        evidence_references: list[dict[str, object]],
        confidence_band: str,
        followup_required: bool,
    ) -> FeedbackGenerationResult:
        chain = self._prompt | self._structured_model
        followup_context = _format_followup_answers(followup_texts)
        payload = chain.invoke(
            {
                "question_code": question.question_code,
                "question_text": question.question_text,
                "question_type": question.question_type,
                "difficulty": question.difficulty,
                "answer_text": answer_text or "(no answer provided)",
                "followup_context": followup_context,
                "reference_context": _format_reference_chunks(evidence_references),
                "criteria_payload": _format_criteria(criteria_results),
                "confidence_band": confidence_band,
                "followup_required": followup_required,
            }
        )
        return FeedbackGenerationResult(
            payload=payload,
            provider="bedrock",
            model_name=self._model_id,
            prompt_version="bedrock_feedback_v4",
        )


class RoutedFeedbackProvider(FeedbackProvider):
    """Prefer Bedrock when configured and fall back locally when it is not."""

    def __init__(self, *, provider_mode: str, region_name: str | None, model_id: str) -> None:
        self._provider_mode = provider_mode
        self._bedrock_provider = None
        if provider_mode == "bedrock" and region_name and _has_aws_credentials(region_name):
            self._bedrock_provider = BedrockFeedbackProvider(region_name=region_name, model_id=model_id)
        self._fallback_provider = LocalFeedbackProvider()

    def generate_feedback(
        self,
        *,
        question: Question,
        answer_text: str,
        followup_texts: list[str] | None = None,
        criteria_results: list[dict[str, object]],
        evidence_references: list[dict[str, object]],
        confidence_band: str,
        followup_required: bool,
    ) -> FeedbackGenerationResult:
        if self._bedrock_provider is not None:
            try:
                return self._bedrock_provider.generate_feedback(
                    question=question,
                    answer_text=answer_text,
                    followup_texts=followup_texts,
                    criteria_results=criteria_results,
                    evidence_references=evidence_references,
                    confidence_band=confidence_band,
                    followup_required=followup_required,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Bedrock evaluation failed for question %s; falling back to local heuristic. Error: %s",
                    question.question_code,
                    exc,
                )
        else:
            logger.warning(
                "Bedrock not configured (check AWS_REGION and credentials); "
                "using local heuristic for question %s.",
                question.question_code,
            )
        return self._fallback_provider.generate_feedback(
            question=question,
            answer_text=answer_text,
            followup_texts=followup_texts,
            criteria_results=criteria_results,
            evidence_references=evidence_references,
            confidence_band=confidence_band,
            followup_required=followup_required,
        )


def _has_aws_credentials(region_name: str) -> bool:
    session = boto3.Session(region_name=region_name)
    credentials = session.get_credentials()
    return credentials is not None
