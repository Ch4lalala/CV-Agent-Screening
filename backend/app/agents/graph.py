"""LangGraph topology for the Phase 5 recruitment workflow."""

from functools import lru_cache, partial

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.candidate import extract_candidate_profile
from app.agents.nodes.evidence import match_evidence
from app.agents.nodes.interview import generate_interview_questions
from app.agents.nodes.report import generate_report
from app.agents.nodes.requirements import normalize_requirements
from app.agents.nodes.security import check_resume_security
from app.agents.nodes.uncertainty import analyze_uncertainty
from app.agents.state import RecruitmentState
from app.ai.client import AIClient, get_ai_client


def build_recruitment_graph(ai_client: AIClient | None = None):
    """Compile the stateful graph, optionally injecting a deterministic test AI."""

    client = ai_client or get_ai_client()
    workflow = StateGraph(RecruitmentState)
    workflow.add_node(
        "normalize_requirements",
        partial(normalize_requirements, ai_client=client),
    )
    workflow.add_node(
        "resume_security",
        partial(check_resume_security, ai_client=client),
    )
    workflow.add_node(
        "extract_candidate_profile",
        partial(extract_candidate_profile, ai_client=client),
    )
    workflow.add_node(
        "match_evidence",
        partial(match_evidence, ai_client=client),
    )
    workflow.add_node("analyze_uncertainty", analyze_uncertainty)
    workflow.add_node(
        "generate_interview_questions",
        partial(generate_interview_questions, ai_client=client),
    )
    workflow.add_node("generate_report", generate_report)

    workflow.add_edge(START, "normalize_requirements")
    workflow.add_edge("normalize_requirements", "resume_security")
    workflow.add_edge("resume_security", "extract_candidate_profile")
    workflow.add_edge("extract_candidate_profile", "match_evidence")
    workflow.add_edge("match_evidence", "analyze_uncertainty")
    workflow.add_edge("analyze_uncertainty", "generate_interview_questions")
    workflow.add_edge("generate_interview_questions", "generate_report")
    workflow.add_edge("generate_report", END)
    return workflow.compile()


@lru_cache(maxsize=1)
def get_recruitment_graph():
    """Return one compiled in-process graph with a lazy shared AI client."""

    return build_recruitment_graph()
