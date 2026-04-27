"""
team/full_session.py — Full Session Mode
Runs all four agents sequentially using direct agent calls (no routing overhead).
"""
import logging
from dataclasses import dataclass, field
from schemas.agent_response import AgentResponse

logger = logging.getLogger(__name__)


@dataclass
class FullSessionResult:
    topic: str
    user_level: str
    professor: AgentResponse | None = None
    ta: AgentResponse | None = None
    librarian: AgentResponse | None = None
    advisor: AgentResponse | None = None
    errors: list = field(default_factory=list)

    @property
    def success(self) -> bool:
        return any(
            a is not None and a.success
            for a in [self.professor, self.ta, self.librarian, self.advisor]
        )

    @property
    def all_doc_urls(self) -> list:
        return [
            (a.doc_title, a.doc_bytes)
            for a in [self.professor, self.ta, self.librarian, self.advisor]
            if a and a.doc_bytes and a.doc_title
        ]


def run_full_session(topic: str, session_id: str = "default", user_level: str = "intermediate") -> FullSessionResult:
    from team.interface import run_teaching_team

    result = FullSessionResult(topic=topic, user_level=user_level)
    prefixes = {
        "professor": "Explain and teach me about",
        "ta":        "Give me practice problems on",
        "librarian": "Find resources and books for",
        "advisor":   "Create a study plan for",
    }
    attrs = ["professor", "ta", "librarian", "advisor"]

    for attr in attrs:
        try:
            resp = run_teaching_team(
                topic=f"{prefixes[attr]}: {topic}",
                session_id=session_id,
                user_level=user_level,
            )
            setattr(result, attr, resp)
        except Exception as e:
            err = f"{attr} failed: {e}"
            logger.error(err)
            result.errors.append(err)
            setattr(result, attr, AgentResponse.error_response(attr, topic, str(e)))

    return result
