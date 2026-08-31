"""Deterministic evaluation service with follow-up triggering and candidate-safe output shaping."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.domain.content import Question, RubricCriterion, WeightConfig
from app.models.domain.interview import EvaluationResult
from app.providers.bedrock import FeedbackProvider
from app.services.retrieval.service import RetrievalService


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]{3,}")


@dataclass(slots=True)
class EvaluationComputation:
    """Result of evaluating a candidate answer before persistence."""

    evaluation: EvaluationResult
    followup_required: bool
    followup_prompt: str | None
    followup_purpose: str | None
    linked_criteria: list[str]


class EvaluationService:
    """Scores answers, computes confidence, and proposes follow-up prompts."""

    def __init__(self, retrieval_service: RetrievalService, feedback_provider: FeedbackProvider) -> None:
        self._retrieval_service = retrieval_service
        self._feedback_provider = feedback_provider

    def evaluate_answer(
        self,
        *,
        session_id: str,
        answer_id: str,
        topic_id: str,
        question: Question,
        rubric_criteria: list[RubricCriterion],
        weight_config: WeightConfig,
        answer_text: str,
        followup_texts: list[str] | None = None,
        followup_answer_id: str | None = None,
        replaces_evaluation_id: str | None = None,
        final_version: bool,
    ) -> EvaluationComputation:
        """Evaluate a primary answer, optionally enriched by follow-up responses."""

        combined_text = answer_text
        if followup_texts:
            combined_text = f"{combined_text} {' '.join(followup_texts)}"

        # Retrieve chunks strictly from question phrasing to avoid answer-key leakage.
        retrieval_query = question.question_text.strip()
        evidence = self._retrieval_service.retrieve(topic_id=topic_id, question_id=question.id, query_text=retrieval_query)

        # Detect answers that cannot merit LLM evaluation.
        latest_answer = followup_texts[-1] if followup_texts else answer_text
        is_question_copy = (
            _is_question_restatement(question.question_text, answer_text)
            or _is_question_restatement(question.question_text, latest_answer)
        )
        is_too_vague = _is_vague_answer(combined_text) or _is_vague_answer(latest_answer)
        force_low_confidence = is_question_copy or is_too_vague

        # Build criteria metadata for the LLM prompt; include description so LLM knows what to assess.
        max_score_total = sum(c.max_score for c in rubric_criteria) or 1.0
        criteria_list: list[dict[str, object]] = [
            {
                "criterion_code": c.criterion_code,
                "criterion_name": c.criterion_name,
                "criterion_description": c.criterion_description,
                "weight": c.weight,
                "score_awarded": 0.0,
                "max_score": c.max_score,
                "reasoning": "",
                "evidence_used": [item["evidence_id"] for item in evidence[:2]],
                "missing_signals": [],
            }
            for c in rubric_criteria
        ]
        followup_count = len(followup_texts) if followup_texts else 0

        if force_low_confidence:
            # Invalid answer — skip LLM, return zeroed scores with a clear explanation.
            normalized_score = 0.0
            percentage = 0.0
            confidence_score = 0.0
            confidence_band = "low"
            feedback_result = _make_invalid_answer_feedback(
                question=question,
                is_question_copy=is_question_copy,
            )
        else:
            followup_eligible = (
                question.followup_enabled
                and followup_count < weight_config.max_followups
            )
            feedback_result = self._feedback_provider.generate_feedback(
                question=question,
                answer_text=answer_text,
                followup_texts=followup_texts or None,
                criteria_results=criteria_list,
                evidence_references=evidence,
                confidence_band="unknown",
                followup_required=followup_eligible,
            )
            normalized_score = round(feedback_result.payload.llm_score or 0.0, 4)
            percentage = round(normalized_score * 100, 2)
            confidence_score = round(feedback_result.payload.llm_confidence or 0.0, 4)
            confidence_band = self._confidence_band(confidence_score, weight_config)

            # Distribute the LLM's overall score proportionally across criteria for audit.
            for item in criteria_list:
                item["score_awarded"] = round(normalized_score * float(item["max_score"]), 4)
                item["reasoning"] = "Assessed by LLM."

        # Only probe further when confidence is genuinely mid; low or high both finalize.
        finalize_decision = (
            "followup_required"
            if (
                not force_low_confidence
                and question.followup_enabled
                and confidence_band == "mid"
                and followup_count < weight_config.max_followups
            )
            else "finalize"
        )
        raw_score = round(sum(float(item["score_awarded"]) for item in criteria_list), 4)

        evaluation = EvaluationResult(
            id=str(uuid.uuid4()),
            candidate_answer_id=answer_id,
            followup_answer_id=followup_answer_id,
            replaces_evaluation_id=replaces_evaluation_id,
            raw_score=raw_score,
            max_score=round(max_score_total, 4),
            normalized_score=normalized_score,
            percentage=percentage,
            confidence_score=confidence_score,
            confidence_band=confidence_band,
            finalize_decision=finalize_decision,
            criteria_results=criteria_list,
            feedback=feedback_result.payload.model_dump(),
            evidence_references=evidence,
            model_metadata={
                "provider": feedback_result.provider,
                "model_name": feedback_result.model_name,
                "prompt_version": feedback_result.prompt_version,
                "llm_used": feedback_result.llm_used,
                "temperature": 0.0,
                "session_id": session_id,
            },
            audit_payload={
                "thresholds_applied": {
                    "low": weight_config.confidence_low,
                    "mid_start": weight_config.confidence_mid_start,
                    "mid_end": weight_config.confidence_mid_end,
                    "high": weight_config.confidence_high,
                },
                "grounding_scope": "question-linked",
                "evaluation_mode": "rescored" if followup_texts else "initial",
                "invalid_answer_reason": (
                    "question_restatement" if is_question_copy else "vague_answer"
                ) if force_low_confidence else None,
            },
            final_version=final_version and finalize_decision == "finalize",
            created_at=datetime.now(timezone.utc),
        )

        linked_criteria = [item["criterion_code"] for item in criteria_list[:2]]
        followup_prompt = feedback_result.payload.followup_prompt
        followup_purpose = feedback_result.payload.followup_purpose
        if finalize_decision == "followup_required" and not followup_prompt and criteria_list:
            focus_name = str(criteria_list[0]["criterion_name"]).lower()
            followup_prompt = f"Can you expand on {focus_name} in your answer?"
            followup_purpose = f"Probe {focus_name} in more detail"

        return EvaluationComputation(
            evaluation=evaluation,
            followup_required=finalize_decision == "followup_required",
            followup_prompt=followup_prompt,
            followup_purpose=followup_purpose,
            linked_criteria=linked_criteria,
        )

    @staticmethod
    def to_candidate_projection(evaluation: EvaluationResult) -> dict[str, object]:
        """Return the candidate-safe evaluation payload."""

        evidence_chunks = [
            {
                "source_label": str(e.get("source_label", e.get("context_code", "Reference"))),
                "excerpt": str(e.get("excerpt", ""))[:300],
                "relevance_score": float(e.get("relevance_score", 0.0)),
            }
            for e in evaluation.evidence_references[:3]
            if e.get("excerpt")
        ]
        return {
            "evaluation_id": evaluation.id,
            "score_percentage": evaluation.percentage,
            "confidence_band": evaluation.confidence_band,
            "strengths": list(evaluation.feedback.get("strengths", [])),
            "gaps": list(evaluation.feedback.get("gaps", [])),
            "summary": str(evaluation.feedback.get("candidate_visible_summary", "")),
            "evidence_chunks": evidence_chunks,
        }

    @staticmethod
    def _confidence_band(score: float, weight_config: WeightConfig) -> str:
        if score < weight_config.confidence_mid_start:
            return "low"
        if score <= weight_config.confidence_mid_end:
            return "mid"
        return "high"

def _make_invalid_answer_feedback(*, question: "Question", is_question_copy: bool) -> "FeedbackGenerationResult":
    """Return a zero-score, LLM-free result for question-restatement and vague answers."""
    from app.providers.bedrock import FeedbackGenerationResult, FeedbackPayload

    if is_question_copy:
        summary = (
            "Your response appears to restate the question rather than answer it. "
            "Please provide an explanation of the concept being asked about."
        )
        gaps = ["Provide an actual answer — explain the concept, don't repeat the question"]
    else:
        summary = (
            "Your response was too brief or did not address the question. "
            "Please provide a more detailed explanation."
        )
        gaps = ["Provide a substantive answer that addresses what the question is asking"]

    return FeedbackGenerationResult(
        payload=FeedbackPayload(
            expected_concepts=[],
            strengths=[],
            gaps=gaps,
            candidate_visible_summary=summary,
            followup_prompt=None,
            followup_purpose=None,
            llm_score=0.0,
            llm_confidence=0.0,
        ),
        provider="guard-rule",
        model_name="invalid-answer-detector",
        prompt_version="guard_v1",
        llm_used=False,
    )


def _is_question_restatement(question_text: str, answer_text: str) -> bool:
    """Return True when the answer is a near-verbatim copy of the question."""
    q_tokens = _tokenize(question_text)
    a_tokens = _tokenize(answer_text)
    if not q_tokens or not a_tokens:
        return False
    overlap = len(q_tokens & a_tokens) / len(q_tokens)
    return overlap >= 0.70


def _is_vague_answer(answer_text: str) -> bool:
    """Return True when the answer has too few meaningful tokens to score."""
    return len(_tokenize(answer_text)) < 6


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}
