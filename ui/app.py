"""
ui/app.py — AI Teaching Team Streamlit UI

Features:
  - Clean answer shown in chat window
  - "For more details check the file below:" + in-memory .docx download button
  - Chat history persisted via SQLite + Redis (survives page refresh)
  - Student progress panel (Feature 1)
  - Prolog prerequisite gate (Feature 2)
  - Full Session mode — all 4 agents (Feature 3)
"""

import streamlit as st
import uuid

from team.interface import run_teaching_team
from team.full_session import run_full_session
from utils.memory import get_progress, get_gap_analysis, clear_progress
from utils.prereq_gate import check_topic_gate
from utils.chat_history import load_history, clear_history, save_message, get_doc_bytes

# ── Constants ──────────────────────────────────────────────────────────────

AGENT_CONFIG = {
    "professor": {"icon": "🎓", "name": "Professor Nova",   "color": "#2E5FA3"},
    "advisor":   {"icon": "🗺️", "name": "Advisor Sage",     "color": "#1E7E34"},
    "librarian": {"icon": "📚", "name": "Librarian Lumen",  "color": "#6C3483"},
    "ta":        {"icon": "✏️", "name": "TA Atlas",         "color": "#B45309"},
    "unknown":   {"icon": "🤖", "name": "AI Teaching Team", "color": "#4A4A4A"},
}

AGENT_DESCRIPTIONS = {
    "professor": "Explains concepts with structured lecture notes",
    "advisor":   "Builds personalised study roadmaps",
    "librarian": "Curates books, courses & research guides",
    "ta":        "Generates practice problems & worked solutions",
}

EXAMPLE_QUERIES = [
    "Explain gradient descent to me",
    "Create a study plan for machine learning",
    "Find resources for learning calculus",
    "Give me practice problems on data structures",
    "What are neural networks and how do they work?",
    "Plan my path to becoming a data scientist",
]

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ── Session state ──────────────────────────────────────────────────────────

def _session_id() -> str:
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    return st.session_state["session_id"]


def _init_state():
    defaults = {
        "messages":     [],          # list of dicts: {role, content, agent, doc_title, doc_bytes}
        "history_loaded": False,     # whether we've loaded from DB this session
        "user_level":   "intermediate",
        "mode":         "single",
        "gate_pending": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _load_history_once():
    """Load chat history from DB on first render (page refresh recovery)."""
    if st.session_state["history_loaded"]:
        return
    st.session_state["history_loaded"] = True
    history = load_history(_session_id())
    if history:
        st.session_state["messages"] = [
            {
                "role":      h["role"],
                "content":   h["content"],
                "agent":     h.get("agent", ""),
                "doc_title": h.get("doc_title", ""),
                "doc_bytes": None,   # lazy-loaded when download is clicked
            }
            for h in history
        ]


# ── Download button helper ─────────────────────────────────────────────────

def _download_button(doc_bytes: bytes | None, doc_title: str, session_id: str, key: str):
    """
    Render the 'For more details' block with a download button.
    If doc_bytes not in memory (history restore), fetches from SQLite.
    """
    if not doc_title:
        return

    # Lazy-load from SQLite if bytes not cached in session state
    if doc_bytes is None:
        doc_bytes = get_doc_bytes(session_id, doc_title)

    if doc_bytes:
        st.markdown("---")
        st.markdown("📄 **For more details check the file below:**")
        filename = doc_title.replace(": ", "_").replace(" ", "_")[:60] + ".docx"
        st.download_button(
            label=f"⬇️  Download  —  {doc_title}",
            data=doc_bytes,
            file_name=filename,
            mime=DOCX_MIME,
            key=key,
            use_container_width=True,
        )
    else:
        st.caption("📄 Document not available (Node.js required for generation).")


# ── Progress panel (Feature 1) ─────────────────────────────────────────────

def _render_progress_panel():
    st.divider()
    st.subheader("📊 Your Progress")
    progress = get_progress(_session_id())
    if not progress:
        st.caption("No topics studied yet. Ask your first question!")
        return
    c1, c2 = st.columns(2)
    c1.metric("Topics", progress.total_topics)
    c2.metric("Unique", len(progress.unique_topics))
    with st.expander("🤖 By Agent", expanded=False):
        for agent_id, topics in progress.topics_by_agent.items():
            cfg = AGENT_CONFIG.get(agent_id, AGENT_CONFIG["unknown"])
            st.markdown(f"**{cfg['icon']} {cfg['name']}** — {len(topics)} session(s)")
            for t in topics[-3:]:
                st.caption(f"  • {t}")
    gap = get_gap_analysis(_session_id())
    if gap:
        with st.expander("🔍 What to Study Next", expanded=True):
            st.markdown(gap.suggested_focus)
            if gap.recommended_next:
                st.markdown("**Ready to learn:**")
                for atom in gap.recommended_next:
                    st.markdown(f"  ✅ {atom.replace('_', ' ').title()}")
    if st.button("🗑️ Reset Progress", use_container_width=True):
        clear_progress(_session_id())
        clear_history(_session_id())
        st.session_state["session_id"] = str(uuid.uuid4())
        st.session_state["messages"] = []
        st.session_state["history_loaded"] = False
        st.rerun()


# ── Prerequisite gate (Feature 2) ─────────────────────────────────────────

def _render_prereq_tree(tree: dict):
    if not tree:
        return
    st.markdown("**Prerequisite map:**")
    all_nodes = set(tree.keys())
    has_parent = {child for children in tree.values() for child in children}
    roots = all_nodes - has_parent

    def _node(n, depth, visited):
        if n in visited or depth > 6:
            return
        visited.add(n)
        indent = "　" * depth
        arrow = "└─ " if depth > 0 else "📌 "
        st.markdown(f"{indent}{arrow}**{n.replace('_', ' ').title()}**")
        for child in tree.get(n, []):
            _node(child, depth + 1, visited)

    visited: set = set()
    for r in sorted(roots):
        _node(r, 0, visited)
    for n in sorted(all_nodes - visited):
        _node(n, 0, visited)


def _render_gate_warning() -> bool:
    if not st.session_state.get("gate_pending"):
        return False
    query, gate_result = st.session_state["gate_pending"]
    st.warning(f"⚠️ {gate_result.warning_message}", icon="📚")
    if gate_result.prereq_tree:
        with st.expander("View prerequisite tree", expanded=False):
            _render_prereq_tree(gate_result.prereq_tree)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Proceed anyway", use_container_width=True, key="gate_proceed"):
            st.session_state["gate_pending"] = None
            _dispatch_query(query, skip_gate=True)
            st.rerun()
    with c2:
        if st.button("❌ Cancel", use_container_width=True, key="gate_cancel"):
            st.session_state["gate_pending"] = None
            st.rerun()
    return True


# ── Message renderer ───────────────────────────────────────────────────────

def _render_message(msg: dict, idx: int):
    role = msg["role"]
    with st.chat_message(role):
        st.markdown(msg["content"])
        if role == "assistant":
            agent = msg.get("agent", "")
            doc_title = msg.get("doc_title", "")
            doc_bytes = msg.get("doc_bytes")
            if agent and agent != "unknown":
                cfg = AGENT_CONFIG.get(agent, AGENT_CONFIG["unknown"])
                st.caption(f"{cfg['icon']} Answered by **{cfg['name']}**")
            if doc_title:
                _download_button(doc_bytes, doc_title, _session_id(), key=f"dl_{idx}_{doc_title[:20]}")


def _render_chat_history():
    for i, msg in enumerate(st.session_state["messages"]):
        _render_message(msg, i)


# ── Query executors ────────────────────────────────────────────────────────

def _execute_single_query(query: str):
    # Add user message to state + persist
    st.session_state["messages"].append({
        "role": "user", "content": query,
        "agent": "", "doc_title": "", "doc_bytes": None,
    })
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            response = run_teaching_team(
                topic=query,
                session_id=_session_id(),
                user_level=st.session_state["user_level"],
            )
        cfg = AGENT_CONFIG.get(response.agent, AGENT_CONFIG["unknown"])

        if response.success:
            st.markdown(response.content)
            st.caption(f"{cfg['icon']} Answered by **{cfg['name']}**")
            if response.doc_title:
                _download_button(
                    response.doc_bytes,
                    response.doc_title,
                    _session_id(),
                    key=f"dl_new_{response.doc_title[:20]}",
                )
        else:
            st.error(f"Error: {response.error}")
            st.markdown(response.content)

    st.session_state["messages"].append({
        "role":      "assistant",
        "content":   response.content,
        "agent":     response.agent,
        "doc_title": response.doc_title,
        "doc_bytes": response.doc_bytes,
    })


def _execute_full_session(topic: str):
    st.session_state["messages"].append({
        "role": "user", "content": topic,
        "agent": "", "doc_title": "", "doc_bytes": None,
    })
    with st.chat_message("user"):
        st.markdown(topic)

    with st.chat_message("assistant"):
        with st.spinner("🚀 Running all four agents — this takes 1–2 minutes…"):
            result = run_full_session(
                topic=topic,
                session_id=_session_id(),
                user_level=st.session_state["user_level"],
            )
        if not result.success:
            st.error("All agents failed. Check Ollama is running.")
            return

        tabs = st.tabs([
            f"{AGENT_CONFIG['professor']['icon']} Professor",
            f"{AGENT_CONFIG['ta']['icon']} TA",
            f"{AGENT_CONFIG['librarian']['icon']} Librarian",
            f"{AGENT_CONFIG['advisor']['icon']} Advisor",
        ])
        agent_resps = [result.professor, result.ta, result.librarian, result.advisor]
        agent_keys  = ["professor", "ta", "librarian", "advisor"]

        for tab, resp, ak in zip(tabs, agent_resps, agent_keys):
            with tab:
                if resp and resp.success:
                    st.markdown(resp.content)
                    if resp.doc_title:
                        _download_button(resp.doc_bytes, resp.doc_title, _session_id(),
                                         key=f"fs_{ak}_{topic[:10]}")
                elif resp:
                    st.warning(f"Agent error: {resp.error}")
                else:
                    st.info("No response.")

    summary = f"**Full Session: {topic}**\n\n" + "\n".join(
        f"{'✅' if (r and r.success) else '❌'} {AGENT_CONFIG[k]['icon']} {AGENT_CONFIG[k]['name']}"
        for r, k in zip(agent_resps, agent_keys)
    )
    st.session_state["messages"].append({
        "role": "assistant", "content": summary,
        "agent": "unknown", "doc_title": "", "doc_bytes": None,
    })


def _dispatch_query(query: str, skip_gate: bool = False):
    query = query.strip()
    if not query:
        return

    if not skip_gate:
        gate = check_topic_gate(query)
        if not gate.gate_cleared:
            st.session_state["gate_pending"] = (query, gate)
            st.rerun()
            return

    if st.session_state["mode"] == "full_session":
        _execute_full_session(query)
    else:
        _execute_single_query(query)


# ── Sidebar ────────────────────────────────────────────────────────────────

def _render_sidebar():
    with st.sidebar:
        st.title("🎓 AI Teaching Team")
        st.caption("Professor · TA · Librarian · Advisor")
        st.divider()

        st.subheader("🔀 Mode")
        mode = st.radio(
            "mode", options=["single", "full_session"], label_visibility="collapsed",
            format_func=lambda x: "⚡ Single Agent" if x == "single" else "🚀 Full Session (all 4 agents)",
        )
        st.session_state["mode"] = mode
        if mode == "full_session":
            st.info("All four agents respond. Results shown in tabs. ~1–2 min.", icon="ℹ️")

        st.divider()
        st.subheader("⚙️ Your Level")
        level = st.radio(
            "level", options=["beginner", "intermediate", "advanced"],
            index=["beginner", "intermediate", "advanced"].index(st.session_state["user_level"]),
            format_func=str.capitalize, label_visibility="collapsed",
        )
        st.session_state["user_level"] = level

        st.divider()
        st.subheader("🤖 The Team")
        for agent_id, desc in AGENT_DESCRIPTIONS.items():
            cfg = AGENT_CONFIG[agent_id]
            st.markdown(f"**{cfg['icon']} {cfg['name']}**  \n<small>{desc}</small>",
                        unsafe_allow_html=True)

        st.divider()
        st.subheader("💡 Try asking")
        for q in EXAMPLE_QUERIES:
            if st.button(q, use_container_width=True, key=f"ex_{q[:20]}"):
                st.session_state["pending_query"] = q
                st.rerun()

        _render_progress_panel()

        st.divider()
        if st.button("🗑️ Clear Chat", use_container_width=True):
            clear_history(_session_id())
            st.session_state["messages"] = []
            st.session_state["gate_pending"] = None
            st.rerun()


# ── Main ───────────────────────────────────────────────────────────────────

def render_app():
    _init_state()
    _load_history_once()   # restore history from DB on refresh
    _render_sidebar()

    mode_label = (
        "🚀 Full Session Mode — all four agents respond"
        if st.session_state["mode"] == "full_session"
        else "Ask anything — your personal professor, advisor, librarian &amp; TA are ready."
    )
    st.markdown(
        f"<h2 style='text-align:center;margin-bottom:0'>🎓 AI Teaching Team</h2>"
        f"<p style='text-align:center;color:grey;margin-top:4px'>{mode_label}</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    if _render_gate_warning():
        return

    if st.session_state.get("pending_query"):
        q = st.session_state.pop("pending_query")
        _dispatch_query(q)
    else:
        _render_chat_history()

    if prompt := st.chat_input("Ask a question or name a topic…"):
        _dispatch_query(prompt)
