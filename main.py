import os
import streamlit as st
from dotenv import load_dotenv
from ui.app import render_app

# Load environment variables
load_dotenv()


def _check_ollama():
    """Warn in the UI if Ollama is unreachable — non-fatal."""
    import urllib.request
    try:
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        urllib.request.urlopen(f"{host}/api/tags", timeout=2)
    except Exception:
        st.warning(
            "⚠️ **Ollama server not detected** at `http://localhost:11434`. "
            "Make sure Ollama is running (`ollama serve`) and that "
            "`qwen3:8b` is pulled (`ollama pull qwen3:8b`).",
            icon="🦙",
        )


def main():
    st.set_page_config(
        page_title="AI Teaching Team",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _check_ollama()
    render_app()


if __name__ == "__main__":
    main()
