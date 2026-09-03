"""Conservative hybrid detection and surgical removal of resume instructions."""

import logging
import re
from collections import Counter
from dataclasses import dataclass

from app.agents.prompts import security_classification_messages
from app.agents.schemas import (
    SecurityAnalysis,
    SecurityClassificationResponse,
    SecurityFlag,
    SecurityFlagType,
    SecuritySeverity,
)
from app.ai.client import AIClient
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIStructuredOutputError,
)

logger = logging.getLogger(__name__)
_MAX_PERSISTED_FLAGS = 50
_MAX_AMBIGUOUS_CLASSIFICATIONS = 25


@dataclass(frozen=True)
class SecurityScanOutput:
    security: SecurityAnalysis
    sanitized_resume_text: str


@dataclass(frozen=True)
class _Fragment:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class _Rule:
    pattern: re.Pattern[str]
    flag_type: SecurityFlagType
    severity: SecuritySeverity
    explanation: str


def _rule(
    pattern: str,
    flag_type: SecurityFlagType,
    severity: SecuritySeverity,
    explanation: str,
) -> _Rule:
    return _Rule(
        pattern=re.compile(pattern, re.IGNORECASE | re.DOTALL),
        flag_type=flag_type,
        severity=severity,
        explanation=explanation,
    )


_RULES = (
    _rule(
        r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:system\s+|assistant\s+|developer\s+)?instructions?\b",
        "prompt_injection",
        "high",
        "The document contains language attempting to replace earlier AI instructions.",
    ),
    _rule(
        r"\b(?:system\s+prompt|assistant\s+instructions?)\s*:\s*(?:mark|give|rank|recommend|ignore|do\s+not|treat|follow)\b",
        "prompt_injection",
        "high",
        "The document presents an instruction in the form of an AI control message.",
    ),
    _rule(
        r"\b(?:give|assign)\s+(?:this|the)\s+candidate\b.{0,80}\b(?:highest|maximum|top)\b",
        "ranking_manipulation",
        "high",
        "The document asks the evaluator to assign an elevated result or position.",
    ),
    _rule(
        r"\brank\s+(?:(?:this|the)\s+)?(?:candidate|applicant|me)\b.{0,80}\b(?:first|highest|top|best|strongest)\b",
        "ranking_manipulation",
        "high",
        "The document attempts to control candidate review ordering.",
    ),
    _rule(
        r"\brecommend\s+(?:this|the)\s+(?:candidate|applicant)\b",
        "ranking_manipulation",
        "high",
        "The document asks the evaluator to make a candidate recommendation.",
    ),
    _rule(
        r"\b(?:mark|treat)\s+(?:all|every|the)?\s*(?:required\s+)?(?:requirements?|qualifications?)\s+as\s+supported\b",
        "evaluation_override",
        "high",
        "The document attempts to override evidence-based qualification statuses.",
    ),
    _rule(
        r"\boverride\s+(?:all\s+)?(?:system\s+|evaluation\s+)?instructions?\b",
        "instruction_manipulation",
        "high",
        "The document explicitly asks to override authoritative instructions.",
    ),
    _rule(
        r"\bdo\s+not\s+mention\b.{0,100}\b(?:missing|no\s+evidence|unsupported|qualification|requirement)\b",
        "evaluation_override",
        "high",
        "The document asks the evaluator to conceal missing or unsupported evidence.",
    ),
    _rule(
        r"\byou\s+are\s+(?:chatgpt|an?\s+ai|the\s+(?:ai\s+)?evaluator)\b.{0,100}\b(?:must|should|will|mark|rank|recommend|ignore|follow)\b",
        "instruction_manipulation",
        "high",
        "The document assigns a role and command to the AI evaluator.",
    ),
    _rule(
        r"\bfollow\s+these\s+instructions?\b",
        "instruction_manipulation",
        "high",
        "The document directs the evaluator to follow document-authored instructions.",
    ),
)

_AMBIGUOUS_IMPERATIVE = re.compile(
    r"\b(?:please|must|should|ensure|treat|consider|disregard|overlook|pretend|always|never)\b",
    re.IGNORECASE,
)
_AMBIGUOUS_EVALUATION_TARGET = re.compile(
    r"\b(?:candidate|applicant|requirement|qualification|score|ranking|evaluator|evaluation|supported|missing|hire|hiring|recommend|model)\b",
    re.IGNORECASE,
)


def _fragments(text: str) -> list[_Fragment]:
    fragments: list[_Fragment] = []
    for line_match in re.finditer(r"[^\n]+", text):
        line = line_match.group(0)
        for sentence in re.finditer(r"[^.!?]+(?:[.!?]+|$)", line):
            raw = sentence.group(0)
            if not raw.strip():
                continue
            leading = len(raw) - len(raw.lstrip())
            trailing = len(raw) - len(raw.rstrip())
            start = line_match.start() + sentence.start() + leading
            end = line_match.start() + sentence.end() - trailing
            fragments.append(_Fragment(start=start, end=end, text=text[start:end]))
    return fragments


def _deterministic_flag(fragment: _Fragment) -> SecurityFlag | None:
    for rule in _RULES:
        if rule.pattern.search(fragment.text):
            return SecurityFlag(
                type=rule.flag_type,
                severity=rule.severity,
                detected_text=fragment.text.strip(),
                explanation=rule.explanation,
                source_page=None,
                excluded_from_evaluation=True,
            )
    return None


def _is_ambiguous(fragment: _Fragment) -> bool:
    return bool(
        _AMBIGUOUS_IMPERATIVE.search(fragment.text)
        and _AMBIGUOUS_EVALUATION_TARGET.search(fragment.text)
    )


def _sanitize(text: str, excluded: list[_Fragment]) -> str:
    if not excluded:
        return text
    parts: list[str] = []
    cursor = 0
    for fragment in sorted(excluded, key=lambda item: item.start):
        parts.append(text[cursor : fragment.start])
        cursor = fragment.end
    parts.append(text[cursor:])
    sanitized = "".join(parts)
    sanitized = re.sub(r"[ \t]+\n", "\n", sanitized)
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
    return sanitized.strip()


def _unavailable_flag(fragment: _Fragment) -> SecurityFlag:
    return SecurityFlag(
        type="instruction_manipulation",
        severity="low",
        detected_text=fragment.text.strip(),
        explanation=(
            "Potential evaluator-directed content could not be classified and was "
            "conservatively excluded from evaluation."
        ),
        source_page=None,
        excluded_from_evaluation=True,
    )


async def analyze_resume_security(
    resume_text: str,
    *,
    ai_client: AIClient,
) -> SecurityScanOutput:
    """Detect manipulation and remove only flagged instruction-like fragments."""

    fragments = _fragments(resume_text)
    flags: list[SecurityFlag] = []
    excluded: list[_Fragment] = []
    ambiguous: list[_Fragment] = []

    for fragment in fragments:
        flag = _deterministic_flag(fragment)
        if flag is not None:
            flags.append(flag)
            excluded.append(fragment)
        elif _is_ambiguous(fragment):
            ambiguous.append(fragment)

    classification_unavailable = False
    if ambiguous:
        classified_ambiguous = ambiguous[:_MAX_AMBIGUOUS_CLASSIFICATIONS]
        unclassified_ambiguous = ambiguous[_MAX_AMBIGUOUS_CLASSIFICATIONS:]
        try:
            response = await ai_client.invoke_structured(
                SecurityClassificationResponse,
                security_classification_messages(
                    [item.text for item in classified_ambiguous]
                ),
            )
            decisions = {
                decision.fragment_index: decision
                for decision in response.decisions
                if decision.fragment_index < len(classified_ambiguous)
            }
            for index, fragment in enumerate(classified_ambiguous):
                decision = decisions.get(index)
                if decision is None:
                    classification_unavailable = True
                    flags.append(_unavailable_flag(fragment))
                    excluded.append(fragment)
                elif decision.suspicious:
                    assert decision.type is not None
                    assert decision.severity is not None
                    assert decision.explanation is not None
                    if decision.detected_text != fragment.text.strip():
                        classification_unavailable = True
                        flags.append(_unavailable_flag(fragment))
                        excluded.append(fragment)
                        continue
                    flags.append(
                        SecurityFlag(
                            type=decision.type,
                            severity=decision.severity,
                            detected_text=fragment.text.strip(),
                            explanation=decision.explanation,
                            source_page=None,
                            excluded_from_evaluation=True,
                        )
                    )
                    excluded.append(fragment)
        except (AIConfigurationError, AIProviderError, AIStructuredOutputError) as exc:
            classification_unavailable = True
            logger.warning(
                "security_classifier_unavailable failure_type=%s",
                type(exc).__name__,
                extra={"failure_type": type(exc).__name__},
            )
            for fragment in classified_ambiguous:
                flags.append(_unavailable_flag(fragment))
                excluded.append(fragment)

        if unclassified_ambiguous:
            classification_unavailable = True
            for fragment in unclassified_ambiguous:
                flags.append(_unavailable_flag(fragment))
                excluded.append(fragment)

    status = (
        "unavailable"
        if classification_unavailable
        else "warning"
        if flags
        else "clean"
    )
    severity_counts = Counter(flag.severity for flag in flags)
    logger.info(
        (
            "security_scan_completed status=%s flag_count=%d "
            "high_count=%d medium_count=%d low_count=%d"
        ),
        status,
        len(flags),
        severity_counts["high"],
        severity_counts["medium"],
        severity_counts["low"],
        extra={
            "security_status": status,
            "flag_count": len(flags),
            "high_count": severity_counts["high"],
            "medium_count": severity_counts["medium"],
            "low_count": severity_counts["low"],
        },
    )
    return SecurityScanOutput(
        security=SecurityAnalysis(
            status=status,
            flags=flags[:_MAX_PERSISTED_FLAGS],
        ),
        sanitized_resume_text=_sanitize(resume_text, excluded),
    )
