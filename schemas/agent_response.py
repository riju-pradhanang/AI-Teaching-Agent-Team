from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class AgentResponse:
    agent: str          # 'professor' | 'advisor' | 'librarian' | 'ta' | 'unknown'
    topic: str
    content: str        # clean markdown text shown in chat
    doc_url: str        # kept for compatibility (empty in V4+)
    doc_title: str      # human-readable document title
    doc_bytes: bytes | None = None   # in-memory docx bytes for download button
    doc_id: str = ""
    search_queries: list = field(default_factory=list)
    word_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error: str = ""
    success: bool = True

    def to_dict(self) -> dict:
        return {
            "agent": self.agent, "topic": self.topic, "content": self.content,
            "doc_url": self.doc_url, "doc_title": self.doc_title,
            "word_count": self.word_count, "timestamp": self.timestamp,
            "error": self.error, "success": self.success,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def error_response(cls, agent: str, topic: str, error_msg: str) -> "AgentResponse":
        return cls(
            agent=agent, topic=topic,
            content=f"Something went wrong: {error_msg}",
            doc_url="", doc_title="", doc_bytes=None,
            error=error_msg, success=False,
        )
