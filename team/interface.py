"""
team/interface.py

Pipeline:
  1. Python keyword router → select correct agent (zero LLM overhead)
  2. Call agent.run() directly → get clean RunOutput
  3. Extract content from RunOutput.content
  4. Prolog validation if applicable
  5. Generate .docx bytes in memory
  6. Persist to chat history (SQLite + Redis)
  7. Record to student memory tracker
  8. Return AgentResponse
"""

import logging
from schemas.agent_response import AgentResponse
from utils.prolog_engine import validate_advisor_plan, validate_ta_solutions
from utils.memory import record_topic
from utils.chat_history import save_message
from tools.doc_generator import generate_docx_bytes
from team.teaching_team import route_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DOC_PREFIXES = {
    "professor": "Lecture",
    "advisor":   "Study Plan",
    "librarian": "Resource Guide",
    "ta":        "Practice Set",
}

_AGENT_LABELS = {
    "professor": "Professor Nova",
    "advisor":   "Advisor Sage",
    "librarian": "Librarian Lumen",
    "ta":        "TA Atlas",
}


def _extract_content(run_output) -> str:
    """Extract clean text from agno RunOutput."""
    # Primary: content field
    try:
        if run_output.content and str(run_output.content).strip():
            return str(run_output.content).strip()
    except Exception:
        pass
    # Fallback: last assistant message
    try:
        for msg in reversed(run_output.messages or []):
            if getattr(msg, "role", "") == "assistant":
                c = getattr(msg, "content", "")
                if c and str(c).strip():
                    return str(c).strip()
    except Exception:
        pass
    return ""


def run_teaching_team(
    topic: str,
    session_id: str = "default",
    user_level: str = "intermediate",
) -> AgentResponse:
    if not topic or not topic.strip():
        return AgentResponse.error_response("unknown", topic, "Topic cannot be empty.")
    if len(topic) > 500:
        return AgentResponse.error_response("unknown", topic, "Topic too long (max 500 chars).")

    try:
        # ── 1. Route ──────────────────────────────────────────────────
        agent_obj, agent_id = route_query(topic)
        agent_label = _AGENT_LABELS.get(agent_id, "AI Teaching Team")
        logger.info("Routing '%s' → %s (level: %s)", topic[:60], agent_id, user_level)

        # ── 2. Run agent directly ─────────────────────────────────────
        prompt = (
            f"[User Level: {user_level}]\n"
            f"[Topic: {topic}]\n\n"
            f"You are {agent_label}. Respond with a complete, well-structured answer "
            f"following your instructions exactly."
        )
        run_output = agent_obj.run(prompt)

        # ── 3. Extract content ────────────────────────────────────────
        content = _extract_content(run_output)
        if not content or len(content.strip()) < 30:
            logger.warning("Agent %s returned empty content for topic: %s", agent_id, topic)
            return AgentResponse.error_response(
                agent_id, topic,
                f"{agent_label} returned an empty response. This may happen if Ollama is slow — please try again."
            )

        # ── 4. Prolog validation ──────────────────────────────────────
        if agent_id == "advisor":
            content = validate_advisor_plan(content, topic)
        elif agent_id == "ta":
            content = validate_ta_solutions(content)

        # ── 5. Generate docx in memory ────────────────────────────────
        doc_title = f"{_DOC_PREFIXES.get(agent_id, 'Document')}: {topic[:60]}"
        doc_bytes = generate_docx_bytes(
            title=doc_title,
            agent=agent_id,
            content=content,
        )
        if not doc_bytes:
            logger.warning("docx generation failed — ensure Node.js is installed")

        # ── 6. Persist chat history ───────────────────────────────────
        save_message(session_id=session_id, role="user",
                     content=topic, user_level=user_level)
        save_message(session_id=session_id, role="assistant",
                     content=content, agent=agent_id,
                     doc_title=doc_title if doc_bytes else "",
                     doc_bytes=doc_bytes, user_level=user_level)

        # ── 7. Student memory ─────────────────────────────────────────
        record_topic(session_id=session_id, topic=topic,
                     agent=agent_id, user_level=user_level)

        logger.info("Done | agent: %s | words: %d | doc: %s",
                    agent_id, len(content.split()),
                    f"{len(doc_bytes)}B" if doc_bytes else "None")

        return AgentResponse(
            agent=agent_id,
            topic=topic,
            content=content,
            doc_url="",
            doc_title=doc_title,
            doc_bytes=doc_bytes,
            word_count=len(content.split()),
            success=True,
            error="",
        )

    except Exception as e:
        logger.error("Team run failed: %s", e, exc_info=True)
        return AgentResponse.error_response("unknown", topic, str(e))
