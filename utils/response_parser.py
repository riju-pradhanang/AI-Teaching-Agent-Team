"""
utils/response_parser.py

Extracts clean agent content from Agno's TeamRunOutput object.

Root cause of previous garbage content:
  str(raw_output) dumps the entire Python dataclass repr including
  run_id, metrics, provider_data etc. — not just the agent's text.

Fix: walk member_responses first (populated when router delegates to
an agent), then fall back to the last assistant message, then content.
"""
import re
import logging
from schemas.agent_response import AgentResponse

logger = logging.getLogger(__name__)


def _extract_clean_content(raw_output) -> tuple[str, str]:
    """
    Returns (clean_text, agent_id) from a TeamRunOutput object.
    Tries sources in priority order — never falls back to str(raw_output).
    """
    # 1. Best source: member_responses — populated when router delegates
    try:
        for resp in (raw_output.member_responses or []):
            content = resp.content
            if content and str(content).strip():
                agent_id = getattr(resp, "agent_id", "") or ""
                return str(content).strip(), agent_id
    except Exception as e:
        logger.debug("member_responses extraction failed: %s", e)

    # 2. Second: TeamRunOutput.content (router responded directly)
    try:
        if raw_output.content and str(raw_output.content).strip():
            return str(raw_output.content).strip(), ""
    except Exception:
        pass

    # 3. Third: last assistant message in messages list
    try:
        for msg in reversed(raw_output.messages or []):
            if getattr(msg, "role", "") == "assistant":
                content = getattr(msg, "content", "")
                if content and str(content).strip():
                    return str(content).strip(), ""
    except Exception as e:
        logger.debug("messages extraction failed: %s", e)

    return "", ""


def _detect_agent(agent_id_from_agno: str, content: str) -> str:
    """Map agno agent_id or content keywords → our agent key."""
    id_map = {
        "professor": "professor",
        "advisor": "advisor",
        "librarian": "librarian",
        "ta": "ta",
        "teachingassistant": "ta",
        "teaching_assistant": "ta",
    }
    if agent_id_from_agno:
        key = agent_id_from_agno.lower().replace("-", "_")
        if key in id_map:
            return id_map[key]

    content_lower = content.lower()
    keyword_map = {
        "professor":  ["overview", "core concepts", "worked example", "misconception", "lecture"],
        "advisor":    ["study plan", "roadmap", "phase", "milestone", "week"],
        "librarian":  ["books", "online course", "articles", "bibliography", "resource guide"],
        "ta":         ["problem", "practice", "solution", "exercise", "quiz"],
    }
    for agent_key, keywords in keyword_map.items():
        if any(kw in content_lower for kw in keywords):
            return agent_key

    return "professor"  # safest default


def parse_agent_output(raw_output, topic: str) -> AgentResponse:
    clean_content, agent_id_raw = _extract_clean_content(raw_output)

    if not clean_content or len(clean_content.strip()) < 30:
        return AgentResponse(
            agent="unknown",
            topic=topic,
            content="The agent returned an empty response. Please try again.",
            doc_url="",
            doc_title="",
            word_count=0,
            success=False,
            error="Empty response from agent.",
        )

    agent = _detect_agent(agent_id_raw, clean_content)

    return AgentResponse(
        agent=agent,
        topic=topic,
        content=clean_content,
        doc_url="",   # will be set by interface.py after docx creation
        doc_title="",
        word_count=len(clean_content.split()),
        success=True,
        error="",
    )
