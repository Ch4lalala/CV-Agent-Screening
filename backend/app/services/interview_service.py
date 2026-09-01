"""Deterministic interview-question eligibility, filtering, and fallback."""

from app.agents.schemas import (
    EvidenceAssessment,
    InterviewQuestion,
    InterviewQuestionsResponse,
)

MAX_INTERVIEW_QUESTIONS = 5
_GENERIC_QUESTIONS = {
    "tell me about yourself",
    "why should we hire you",
    "what are your strengths",
    "what are your weaknesses",
}


def eligible_uncertainties(
    assessments: list[EvidenceAssessment],
) -> list[EvidenceAssessment]:
    eligible = [
        item
        for item in assessments
        if item.status == "partial"
        or (item.status == "no_evidence" and item.requirement_type == "required")
        or item.needs_human_verification
    ]
    return sorted(
        eligible,
        key=lambda item: (
            item.requirement_type != "required",
            item.status != "partial",
            item.requirement_index,
        ),
    )[:MAX_INTERVIEW_QUESTIONS]


def _is_generic(question: str) -> bool:
    normalized = question.casefold().strip().rstrip("?.!")
    return normalized in _GENERIC_QUESTIONS


def _fallback_question(assessment: EvidenceAssessment) -> str:
    if assessment.evidence:
        quote = " ".join(assessment.evidence[0].quote.split())
        if len(quote) > 180:
            quote = f"{quote[:177]}..."
        return (
            f'The resume states "{quote}". Could you clarify how this experience '
            f"demonstrates {assessment.requirement}?"
        )
    return (
        f"Could you describe any experience with {assessment.requirement}, "
        "including a specific example and your role?"
    )


def reconcile_interview_questions(
    assessments: list[EvidenceAssessment],
    ai_response: InterviewQuestionsResponse,
) -> list[InterviewQuestion]:
    eligible = eligible_uncertainties(assessments)
    drafts_by_index = {}
    for draft in ai_response.questions:
        if not _is_generic(draft.question):
            drafts_by_index.setdefault(draft.requirement_index, draft)

    questions: list[InterviewQuestion] = []
    seen: set[str] = set()
    for assessment in eligible:
        draft = drafts_by_index.get(assessment.requirement_index)
        question = draft.question if draft is not None else _fallback_question(assessment)
        question_key = " ".join(question.casefold().split())
        if question_key in seen:
            continue
        seen.add(question_key)
        questions.append(
            InterviewQuestion(
                requirement=assessment.requirement,
                requirement_type=assessment.requirement_type,
                question=question,
                reason=assessment.explanation,
            )
        )
    return questions[:MAX_INTERVIEW_QUESTIONS]
