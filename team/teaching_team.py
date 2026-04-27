"""
team/teaching_team.py

ARCHITECTURE CHANGE (V5 fix):
  Previous: Agno Team in route mode — router called delegate_task_to_member()
            as a tool call. qwen3:8b failed to generate valid tool call JSON,
            causing empty member_responses and the "Empty response" error.

  Now: Python-level keyword router — zero LLM calls for routing.
       Routes directly to the correct Agent instance based on query keywords.
       Each agent still runs its full LLM call with qwen3:8b.
       Result: reliable routing + one fewer LLM call = faster responses.
"""

import re
from agents.professor_agent import professor_agent
from agents.advisor_agent import advisor_agent
from agents.librarian_agent import librarian_agent
from agents.teaching_assistant_agent import teaching_assistant_agent


# ── Routing rules (priority order) ────────────────────────────────────────

_RULES = [
    # TA — must come before professor to catch "explain AND practice" requests
    (teaching_assistant_agent, "ta", [
        "practice", "quiz", "exercise", "problem", "test me", "drill",
        "challenge me", "give me questions", "generate problems", "homework",
    ]),
    # Advisor
    (advisor_agent, "advisor", [
        "study plan", "roadmap", "schedule", "path to", "how do i become",
        "plan my", "guide me", "advise", "learning path", "curriculum",
        "week", "phase", "milestones",
    ]),
    # Librarian
    (librarian_agent, "librarian", [
        "find sources", "resources", "books", "articles", "papers",
        "references", "bibliography", "recommend reading", "where can i learn",
        "online course", "best website", "find me",
    ]),
    # Professor — default for explain/teach/what/how
    (professor_agent, "professor", [
        "explain", "what is", "what are", "how does", "how do",
        "teach me", "describe", "define", "difference between",
        "tell me about", "introduction to", "overview of", "summarize",
    ]),
]

_DEFAULT_AGENT = (professor_agent, "professor")


def route_query(query: str) -> tuple:
    """
    Returns (agent_instance, agent_id_str) based on keyword matching.
    Falls back to professor (best default for open-ended questions).
    """
    q = query.lower()
    for agent_obj, agent_id, keywords in _RULES:
        if any(kw in q for kw in keywords):
            return agent_obj, agent_id
    return _DEFAULT_AGENT
