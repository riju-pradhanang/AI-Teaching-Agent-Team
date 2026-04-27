# 🎓 AI Teaching Agent Team

> A local, free, multi-agent AI teaching system powered by **Ollama** — four specialised agents that explain, plan, curate, and practice with you. Fully offline, no cloud API costs, with persistent chat history, Prolog-powered prerequisite gating, and downloadable Word document output.

---

## Table of Contents

- [Overview](#overview)
- [What's New vs V1](#whats-new-vs-v1)
- [System Architecture](#system-architecture)
- [The Four Agents](#the-four-agents)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [How It Works](#how-it-works)
- [Feature Guide](#feature-guide)
- [Output Schema](#output-schema)
- [Integration Contract](#integration-contract)
- [Prolog Knowledge Base](#prolog-knowledge-base)
- [Chat History Architecture](#chat-history-architecture)
- [Document Generation](#document-generation)
- [Routing Logic](#routing-logic)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Known Limitations](#known-limitations)

---

## Overview

The AI Teaching Agent Team is a production-grade multi-agent system that routes educational queries to the most appropriate specialist. Instead of one generic AI, four dedicated agents each own a distinct teaching function:

| Query Intent | Agent | Persona | Output |
|---|---|---|---|
| Explain / teach / what is / how does | **Professor** | Professor Nova 🎓 | Structured lecture notes |
| Plan / roadmap / study schedule | **Advisor** | Advisor Sage 🗺️ | Phased study plan |
| Find sources / resources / books | **Librarian** | Librarian Lumen 📚 | Annotated resource guide |
| Practice / quiz / problems | **TA** | TA Atlas ✏️ | Practice set + solutions |

Every response is shown directly in the chat window and also saved as a **downloadable `.docx` Word document** generated in memory — no files written to disk, no cloud storage required.

---

## What's New vs V1

| Feature | V1 | Final |
|---|---|---|
| LLM | OpenAI GPT-4o-mini (paid, cloud) | **qwen2.5:7b / mistral:7b via Ollama (free, local)** |
| Document output | Google Docs via Composio | **In-memory .docx download button** |
| Routing | Agno Team `route` mode (LLM call) | **Python keyword router (instant, zero tokens)** |
| Chat history | Session state only (lost on refresh) | **SQLite (durable) + Redis (fast cache)** |
| Student tracking | None | **Per-session memory + gap analysis** |
| Prerequisite awareness | None | **Prolog knowledge base with advisory gate** |
| Full-session mode | None | **All 4 agents respond in tabs** |
| Internet required | Yes | **No (optional for SerpAPI search)** |
| Cost per query | ~$0.0004 | **$0.00** |

---

## System Architecture

```
User Query (Streamlit UI)
         │
         ▼
  Python Keyword Router          ← Zero LLM overhead, instant
  (team/teaching_team.py)
         │
    ┌────┴─────────────────────────┐
    │  Keyword match → agent ID   │
    └────┬─────────────────────────┘
         │
    ┌────▼────┐  ┌────────┐  ┌───────────┐  ┌──────┐
    │Professor│  │Advisor │  │ Librarian │  │  TA  │
    │ Nova    │  │  Sage  │  │   Lumen   │  │Atlas │
    │qwen2.5  │  │qwen2.5 │  │ mistral   │  │mistr │
    │  :7b    │  │  :7b   │  │   :7b     │  │al:7b │
    └────┬────┘  └───┬────┘  └─────┬─────┘  └──┬───┘
         └───────────┴─────────────┴────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   team/interface   │
                    │  • Extract content │
                    │  • Prolog validate │
                    │  • Generate .docx  │
                    │  • Save to DB      │
                    │  • Record memory   │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │    AgentResponse   │
                    │  content (chat)    │
                    │  doc_bytes (docx)  │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │   Streamlit UI     │
                    │  • Show in chat    │
                    │  • Download button │
                    │  • Progress panel  │
                    └────────────────────┘

Persistence Layer:
  SQLite ──────── chat_history.db     (durable, all messages + doc bytes)
  SQLite ──────── student_memory.db   (topic history, gap analysis)
  Redis  ──────── hot cache           (last 50 messages, fast read)
                  (optional — falls back to SQLite if unavailable)

Prolog Layer (optional):
  SWI-Prolog ──── knowledge_base.pl   (prerequisites, difficulty, validation)
```

![System Architecture](/images/system_architecture_diagram.svg)

---

## The Four Agents

### 🎓 Professor Nova
**Model:** `qwen2.5:7b` | **Trigger:** explain, what is, how does, teach me, describe, define, overview  
**Output structure:**
```
## Overview          — 2-3 paragraphs from first principles
## Core Concepts     — 4-5 bullets with bold concept names
## Worked Example    — numbered step-by-step walkthrough
## Common Misconceptions — 2-3 bullets: myth vs reality
## Summary           — what it is, why it matters, what to learn next
```

### 🗺️ Advisor Sage
**Model:** `qwen2.5:7b` | **Trigger:** study plan, roadmap, schedule, path to, how do I become, curriculum  
**Output structure:**
```
## Goal              — what the student will achieve
## Prerequisites     — what to know first
## Study Plan        — Phase 1 / 2 / 3 with weekly tasks
## Milestones        — numbered measurable checkpoints
## Resources         — curated tools and materials
## Summary           — 2 sentences on the path
```

### 📚 Librarian Lumen
**Model:** `mistral:7b` | **Trigger:** find resources, books, articles, papers, references, where can I learn  
**Output structure:**
```
## Introduction      — overview of the learning landscape
## Books             — 3-5 with author and annotation
## Online Courses    — 3-5 with platform
## Articles & Papers — 3-5 with source
## Practice & Tools  — 2-3 interactive resources
## Summary           — best starting point and order
```

### ✏️ TA Atlas
**Model:** `mistral:7b` | **Trigger:** practice, quiz, exercise, problems, test me, homework  
**Output structure:**
```
## Introduction      — topic and difficulty level
## Problems          — 5 problems (Easy/Medium/Hard labelled)
## Solutions         — Step 1 / Step 2 / Answer for each
## Key Takeaways     — 3 bullets summarising lessons
```

---

## Key Features

### ⚡ Feature 1 — Student Memory & Progress Tracking
Every topic you study is recorded in `data/student_memory.db`. The sidebar shows:
- Total topics and unique topics studied
- Breakdown by which agent answered
- **Gap analysis** — using the Prolog prerequisite graph, surfaces the top 5 topics you're ready to learn next (all prerequisites covered)

### 🧠 Feature 2 — Prolog Prerequisite Gating
When you ask about an advanced topic (e.g., Deep Learning), a yellow advisory banner shows:
- Which prerequisites you should know first
- A collapsible visual prerequisite tree
- **Proceed anyway** or **Cancel** buttons

The gate is advisory only — it never hard-blocks learning. Requires SWI-Prolog (optional).

### 🚀 Feature 3 — Full Session Mode
Switch to **Full Session** in the sidebar. All four agents respond to your topic sequentially and results are displayed in four tabs:
1. Professor explains the concept
2. TA generates practice problems
3. Librarian finds resources  
4. Advisor builds a study plan

Each tab has its own download button.

### 📄 Downloadable Word Documents
Every response automatically generates a professional `.docx` file:
- Agent-branded colour scheme and header/footer
- Proper heading hierarchy, bullet lists, numbered lists
- Rendered entirely in memory — no files stored on disk
- One-click download from the chat window

### 💾 Persistent Chat History
Chat history survives page refresh and browser restarts:
- **Redis** (if running): fast hot cache, last 50 messages per session
- **SQLite** (always): permanent durable storage including doc bytes
- Redis is optional — falls back to SQLite silently if unavailable

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.11+ | Core development |
| Agent Framework | Agno ≥ 1.0.0 | Agent orchestration |
| LLM (Professor/Advisor) | qwen2.5:7b via Ollama | Free, local inference |
| LLM (Librarian/TA) | mistral:7b via Ollama | Free, local inference |
| Routing | Python keyword matching | Zero-latency, zero-token routing |
| UI | Streamlit ≥ 1.35.0 | Chat interface |
| Document generation | docx (Node.js) + doc_generator.py | Professional .docx in memory |
| Chat persistence | SQLite + Redis | Durable history + fast cache |
| Student memory | SQLite | Per-session topic tracking |
| Prerequisite logic | SWI-Prolog + pyswip | Knowledge graph + gate |
| Environment | python-dotenv | Config management |

---

## Project Structure

```
AI_Teaching_Agent_Team/
│
├── main.py                          # Entry point — Streamlit + Ollama health check
├── generate_docx.js                 # Node.js docx generator (called via subprocess)
├── package.json                     # Node.js dependency (docx ^9.x)
├── requirements.txt                 # Python dependencies
├── .env                             # API keys and config — never commit
├── .gitignore
│
├── agents/                          # Agent definitions
│   ├── professor_agent.py           # Professor Nova — qwen2.5:7b
│   ├── advisor_agent.py             # Advisor Sage  — qwen2.5:7b
│   ├── librarian_agent.py           # Librarian Lumen — mistral:7b
│   └── teaching_assistant_agent.py  # TA Atlas — mistral:7b
│
├── team/
│   ├── teaching_team.py             # Python keyword router
│   ├── interface.py                 # ⭐ Main pipeline — route → run → docx → save
│   └── full_session.py              # Full Session mode — all 4 agents
│
├── ui/
│   └── app.py                       # Streamlit UI — all 3 features integrated
│
├── schemas/
│   └── agent_response.py            # AgentResponse dataclass
│
├── tools/
│   ├── doc_generator.py             # Python wrapper for generate_docx.js
│   └── search_tools.py              # SerpAPI web search (optional)
│
├── utils/
│   ├── chat_history.py              # SQLite + Redis persistence
│   ├── memory.py                    # Student progress + gap analysis
│   ├── prereq_gate.py               # Prolog prerequisite gate
│   ├── prolog_engine.py             # SWI-Prolog bridge (pyswip)
│   └── response_parser.py           # Extracts clean content from RunOutput
│
├── prolog/
│   └── knowledge_base.pl            # Prerequisites, difficulty, validation rules
│
├── tests/
│   └── test_agents.py               # Test suite
│
├── images/
│   └── system_architecture_diagram.svg
│
└── data/                            # Auto-created at runtime
    ├── chat_history.db              # SQLite: all messages + doc bytes
    └── student_memory.db            # SQLite: topic history per session
```

---

## Prerequisites

| Requirement | Version | Purpose | Required? |
|---|---|---|---|
| Python | 3.11+ | Core runtime | ✅ Yes |
| Ollama | Latest | Local LLM server | ✅ Yes |
| Node.js | 18+ | docx file generation | ✅ Yes |
| Redis | 7+ | Fast chat history cache | ⚠️ Optional |
| SWI-Prolog | Latest | Prerequisite gate | ⚠️ Optional |

---

## Installation & Setup

### Step 1 — Install Ollama

**macOS / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:** Download from https://ollama.com/download and run the installer.

### Step 2 — Pull the required models

```bash
# Keep Ollama server running in one terminal:
ollama serve

# Pull models in another terminal (one-time, ~8GB total):
ollama pull qwen2.5:7b
ollama pull mistral:7b
```

### Step 3 — Install Node.js and docx package

Download Node.js 18+ from https://nodejs.org (LTS version).

Then install the docx package locally in the project folder:
```bash
cd AI_Teaching_Agent_Team
npm install docx
```

> **Important:** Use `npm install` (local), not `npm install -g` (global). The script requires a local `node_modules/docx` folder.

### Step 4 — Create and activate a Python virtual environment

```bash
python -m venv venv

# macOS / Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### Step 5 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 6 — Install Redis (optional but recommended)

**Windows (WSL2):**
```bash
wsl sudo apt install redis-server
wsl redis-server --daemonize yes
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu / Debian:**
```bash
sudo apt install redis-server
sudo systemctl start redis
```

If Redis is not running, the app falls back to SQLite-only history automatically — no crash, no configuration needed.

### Step 7 — Install SWI-Prolog (optional)

Required only for the prerequisite gate feature.

**macOS:** `brew install swi-prolog`  
**Ubuntu:** `sudo apt-get install swi-prolog`  
**Windows:** Download from https://www.swi-prolog.org/download/stable

### Step 8 — Configure environment variables

Copy and edit the `.env` file:

```bash
cp .env .env.backup   # optional backup
```

Then open `.env` and fill in your values (see [Environment Variables](#environment-variables)).

---

## Environment Variables

```env
# ── Ollama (required) ──────────────────────────────────────────
OLLAMA_HOST=http://localhost:11434

# ── SerpAPI (optional — enables web search inside agents) ──────
SERPAPI_API_KEY=your-serpapi-key-here

# ── Persistence ────────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_TTL=86400

CHAT_DB_PATH=data/chat_history.db
STUDENT_DB_PATH=data/student_memory.db

# ── Debug ──────────────────────────────────────────────────────
DEBUG=false
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `OLLAMA_HOST` | No | `http://localhost:11434` | Ollama server URL |
| `SERPAPI_API_KEY` | No | — | Enables live web search in agents |
| `REDIS_HOST` | No | `localhost` | Redis host |
| `REDIS_PORT` | No | `6379` | Redis port |
| `REDIS_TTL` | No | `86400` | Session cache TTL in seconds (24h) |
| `CHAT_DB_PATH` | No | `data/chat_history.db` | SQLite chat history path |
| `STUDENT_DB_PATH` | No | `data/student_memory.db` | SQLite memory DB path |
| `DEBUG` | No | `false` | Set `true` for verbose agent logs |

---

## Running the App

```bash
# Ensure Ollama is running first:
ollama serve

# Then launch:
streamlit run main.py
```

Opens at **http://localhost:8501**

On startup, the app checks if Ollama is reachable and shows a warning banner if not — it will not crash.

### Run tests

```bash
python -m pytest tests/test_agents.py -v
```

---

## How It Works

### Request lifecycle

```
1. User types a query in the chat input
2. Prerequisite gate checks topic against Prolog graph (if SWI-Prolog installed)
   → If advanced topic with unmet prereqs: show advisory warning
   → User can proceed anyway or cancel
3. Python keyword router maps query to agent ID (instant, no LLM call)
4. interface.py builds prompt: [User Level: X] + [Topic: Y] + instructions
5. Agent calls agent_obj.run(prompt) → Ollama generates response
6. response_parser extracts clean text from RunOutput.content
7. Prolog validation runs (advisor plan structure check / TA solution check)
8. generate_docx_bytes() calls Node.js → generates .docx bytes in memory
9. save_message() persists to SQLite and pushes to Redis cache
10. record_topic() updates student memory DB
11. AgentResponse returned to UI
12. UI renders: markdown in chat + agent badge + download button
```

---

## Feature Guide

### Single Agent Mode (default)

Type any question in the chat input. The Python router picks the best agent automatically. A download button appears below every response.

**Example queries:**
- `"Explain gradient descent to me"` → Professor Nova
- `"Create a study plan for machine learning"` → Advisor Sage
- `"Find resources for learning calculus"` → Librarian Lumen
- `"Give me practice problems on data structures"` → TA Atlas

### Full Session Mode

Click **🚀 Full Session** in the sidebar radio buttons. All four agents respond to your topic and results appear in four labelled tabs. Each tab has its own download button. Takes approximately 2–5 minutes depending on hardware.

### Progress Panel

The sidebar bottom shows your learning progress for the current session. After several queries, the **"What to Study Next"** section appears showing topics whose prerequisites you've now covered, based on the Prolog graph.

### Prerequisite Gate

When you ask about an advanced topic like Deep Learning or Dynamic Programming, a yellow warning appears listing what you should know first. Click **"Proceed anyway"** to continue or **"Cancel"** to rethink. The gate is never a hard block.

### Chat History Recovery

If you refresh the page or close and reopen the browser, your previous chat is restored from the database. The same `session_id` (stored in browser session state) is used to load your history from SQLite.

---

## Output Schema

```python
@dataclass
class AgentResponse:
    agent: str            # 'professor' | 'advisor' | 'librarian' | 'ta' | 'unknown'
    topic: str            # Original user query
    content: str          # Structured markdown — displayed in chat
    doc_url: str          # Empty string (legacy field, kept for compatibility)
    doc_title: str        # e.g. "Lecture: Gradient Descent"
    doc_bytes: bytes | None  # Raw .docx bytes for download button
    word_count: int       # Word count of content
    timestamp: str        # UTC ISO 8601
    success: bool         # False if any error occurred
    error: str            # Error message (empty if success=True)
```

**Usage in UI:**
```python
from team.interface import run_teaching_team

response = run_teaching_team(
    topic="Explain neural networks",
    session_id="user-session-uuid",
    user_level="intermediate",
)

if response.success:
    print(response.content)          # show in chat
    if response.doc_bytes:
        # serve as download button
        st.download_button("Download", response.doc_bytes, "lecture.docx")
else:
    print(response.error)
```

---

## Integration Contract

The UI imports exactly one function:

```python
from team.interface import run_teaching_team
```

**Signature:**
```python
def run_teaching_team(
    topic: str,            # 1–500 characters
    session_id: str,       # UUID per user session
    user_level: str,       # 'beginner' | 'intermediate' | 'advanced'
) -> AgentResponse:        # always returns, never raises
```

**UI responsibilities:**
- Generate and store `session_id` once per browser session
- Check `response.success` before rendering content
- Pass `response.doc_bytes` directly to `st.download_button()`
- Never call agents directly — always go through `run_teaching_team()`

---

## Prolog Knowledge Base

Located at `prolog/knowledge_base.pl`. Defines three types of facts:

### prerequisite/2
```prolog
prerequisite(algebra, calculus).
prerequisite(calculus, machine_learning).
prerequisite(programming_basics, data_structures).
% ... 20+ relationships across maths and CS
```

### topic_difficulty/2
```prolog
topic_difficulty(algebra, beginner).
topic_difficulty(calculus, intermediate).
topic_difficulty(machine_learning, advanced).
topic_difficulty(deep_learning, advanced).
```

### prerequisite_chain/2 (transitive)
```prolog
prerequisite_chain(X, Y) :- prerequisite(X, Y).
prerequisite_chain(X, Y) :- prerequisite(X, Z), prerequisite_chain(Z, Y).
```

**To add a new topic:**
```prolog
prerequisite(your_topic, advanced_topic).
topic_difficulty(your_topic, intermediate).
```

---

## Chat History Architecture

```
Write path:  interface.py
               └─ save_message()
                    ├─ INSERT INTO chat_messages (SQLite) ← always
                    └─ RPUSH chat:{session_id} (Redis)    ← if available

Read path:   ui/app.py _load_history_once()
               └─ load_history(session_id)
                    ├─ LRANGE chat:{session_id} (Redis)   ← try first (fast)
                    └─ SELECT FROM chat_messages (SQLite) ← fallback

Doc bytes:   stored as BLOB in SQLite only (Redis holds lightweight JSON)
             fetched on-demand by get_doc_bytes() when download clicked
```

**SQLite schema:**
```sql
CREATE TABLE chat_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT    NOT NULL,
    role       TEXT    NOT NULL,       -- 'user' | 'assistant'
    content    TEXT    NOT NULL,
    agent      TEXT    NOT NULL DEFAULT '',
    doc_title  TEXT    NOT NULL DEFAULT '',
    doc_bytes  BLOB,                   -- .docx bytes, nullable
    user_level TEXT    NOT NULL DEFAULT 'intermediate',
    timestamp  TEXT    NOT NULL
);
```

---

## Document Generation

Documents are generated by `generate_docx.js` (Node.js, called via subprocess) and returned as raw bytes. They are never written to disk — bytes are stored in SQLite for later re-download.

**Features of generated documents:**
- Agent-branded colour scheme (blue for Professor, green for Advisor, purple for Librarian, amber for TA)
- Professional header with agent name and date
- Page-numbered footer
- Proper heading hierarchy (H1 banner, H2 section, H3 subsection)
- Bullet lists with correct indentation
- Numbered lists
- Inline bold/italic/code formatting
- Footer attribution line

**To regenerate manually:**
```bash
echo '{"title":"Test","agent":"professor","content":"## Overview\nHello world","date":"May 1, 2026"}' | node generate_docx.js > test.docx
```

---

## Routing Logic

The router (`team/teaching_team.py`) uses keyword matching with priority ordering:

```python
_RULES = [
    (ta_agent,        "ta",        ["practice", "quiz", "exercise", "problem", ...]),
    (advisor_agent,   "advisor",   ["study plan", "roadmap", "schedule", ...]),
    (librarian_agent, "librarian", ["find sources", "resources", "books", ...]),
    (professor_agent, "professor", ["explain", "what is", "how does", ...]),
]
# Default fallback: professor
```

TA is checked first to catch queries like "explain and give me practice problems" correctly. Professor is the catch-all default for open-ended questions.

**Adding routing keywords:**
Edit `_RULES` in `team/teaching_team.py`. No other file needs to change.

---

## Testing

```bash
python -m pytest tests/test_agents.py -v
```

| Test | Checks |
|---|---|
| `test_response_schema` | AgentResponse fields are correct types |
| `test_professor_routing` | Explanation queries → professor |
| `test_advisor_routing` | Planning queries → advisor |
| `test_librarian_routing` | Research queries → librarian |
| `test_ta_routing` | Practice queries → ta |
| `test_empty_topic` | Empty input caught before model call |
| `test_route_query_keywords` | All routing rules return expected agent IDs |

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Yellow "Ollama not detected" banner | Ollama not running | Run `ollama serve` |
| "Empty response from agent" error | Model not pulled | Run `ollama pull qwen2.5:7b` and `ollama pull mistral:7b` |
| No download button appears | Node.js `docx` not installed | Run `npm install docx` inside the project folder (not `-g`) |
| `Cannot find module 'docx'` | Global install used instead of local | `cd AI_Teaching_Agent_Team && npm install docx` |
| Redis unavailable warning in logs | Redis not running | Start Redis, or ignore — SQLite fallback is automatic |
| Prolog features disabled | SWI-Prolog not installed | Install SWI-Prolog (optional feature) |
| Very slow responses (>3 min) | Model running on CPU | Check `ollama ps` — ensure GPU is being used if available |
| Response truncated mid-sentence | `num_predict` too low | Increase `num_predict` in agent files (default: 900) |
| `sqlite3.OperationalError` | Missing `data/` folder | Run `mkdir data` in project root |

---

## Known Limitations

| Limitation | Notes |
|---|---|
| English only | No multilingual support |
| CPU inference is slow | ~30–90s per query on CPU. GPU reduces this to ~5–15s |
| No streaming output | Full response appears at once, not word-by-word |
| Session ID is browser-local | Different browsers = different chat history |
| SerpAPI web search is optional | Agents use training knowledge when not configured |
| Full Session mode is slow | Runs 4 sequential LLM calls — expect 2–5 minutes |

---

## License

MIT License.

---

*Built with Python, Agno, Ollama, Streamlit, Node.js docx, SQLite, Redis, and SWI-Prolog.*  
*100% local. 100% free.*