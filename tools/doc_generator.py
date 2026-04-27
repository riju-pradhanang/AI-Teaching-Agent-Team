"""
tools/doc_generator.py

Generates professional .docx bytes by calling generate_docx.js via subprocess.
Returns raw bytes — caller decides whether to save to disk or serve in memory.

Public API:
    generate_docx_bytes(title, agent, content) -> bytes | None
"""

import json
import subprocess
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the JS generator — same directory as project root
_JS_PATH = Path(__file__).parent.parent / "generate_docx.js"


def generate_docx_bytes(title: str, agent: str, content: str) -> bytes | None:
    """
    Generate a .docx file using docx-js and return raw bytes.
    Returns None on any failure (caller should handle gracefully).
    """
    if not _JS_PATH.exists():
        logger.error("generate_docx.js not found at %s", _JS_PATH)
        return None

    payload = json.dumps({
        "title": title,
        "agent": agent,
        "content": content,
        "date": datetime.now().strftime("%B %d, %Y"),
    })

    try:
        result = subprocess.run(
            ["node", str(_JS_PATH)],
            input=payload.encode(),
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("generate_docx.js error: %s", result.stderr.decode())
            return None
        if not result.stdout:
            logger.error("generate_docx.js returned empty output")
            return None
        logger.info("Generated docx: %d bytes for '%s'", len(result.stdout), title)
        return result.stdout

    except FileNotFoundError:
        logger.error("node not found. Install Node.js to enable docx generation.")
        return None
    except subprocess.TimeoutExpired:
        logger.error("generate_docx.js timed out")
        return None
    except Exception as e:
        logger.error("generate_docx_bytes failed: %s", e)
        return None
