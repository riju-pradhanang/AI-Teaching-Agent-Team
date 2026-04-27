# 🎓 AI Teaching Agent Team

A multi-agent AI system that routes educational queries to four specialized agents — each one generating structured content and saving it as a Google Doc. Built with Python, Agno, OpenAI GPT-4o-mini, Composio, SerpAPI, and Streamlit.

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [The Four Agents](#the-four-agents)
- [Tech Stack](#tech-stack)
- [Team Structure](#team-structure)
- [Project File Structure](#project-file-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Environment Configuration](#environment-configuration)
- [Running the App](#running-the-app)
- [How It Works](#how-it-works)
- [Agent Details](#agent-details)
  - [Professor Agent](#professor-agent)
  - [Academic Advisor Agent](#academic-advisor-agent)
  - [Research Librarian Agent](#research-librarian-agent)
  - [Teaching Assistant Agent](#teaching-assistant-agent)
- [Output Schema](#output-schema)
- [Integration Contract (for UI)](#integration-contract-for-ui)
- [Tool Integration](#tool-integration)
- [Testing](#testing)
- [Cost & Token Budget](#cost--token-budget)
- [Known Limitations (v1)](#known-limitations-v1)
- [Contributing](#contributing)

---

## Overview

The AI Teaching Agent Team is a production-grade multi-agent system designed to assist learners by routing their educational queries to the most appropriate AI agent. Instead of one generic AI trying to do everything, four specialized agents each own a distinct teaching function:

| Need | Agent | What It Produces |
|------|-------|-----------------|
| "Explain this topic to me" | Professor Agent | Structured lecture note |
| "Help me plan how to learn this" | Academic Advisor Agent | Phased study roadmap |
| "Find me papers and resources" | Research Librarian Agent | Annotated bibliography |
| "Give me practice problems" | Teaching Assistant Agent | Problem set + full solutions |

Every agent response is saved as a **Google Doc via Composio**, and the document link is returned to the user alongside the text response.

---

## System Architecture

```
User Query
    │
    ▼
Agno Team (mode: "route")
    │   GPT-4o-mini classifies intent
    │
    ├──── "explain / teach"  ──▶  Professor Agent ──▶ Google Doc
    ├──── "plan / advise"    ──▶  Advisor Agent   ──▶ Google Doc
    ├──── "find / research"  ──▶  Librarian Agent ──▶ Google Doc
    └──── "practice / quiz"  ──▶  TA Agent        ──▶ Google Doc
                                       │
                                       ▼
                               AgentResponse object
                              (content + doc_url + metadata)
                                       │
                                       ▼
                               Streamlit UI (Role 3)
```

![System Architecture](/images/system_architecture_diagram.svg)

**Design decisions:**

- **Route mode, not collaborate mode.** Each query goes to exactly one agent. This keeps latency low, cost predictable, and debugging straightforward.
- **One new Google Doc per response.** No updating of existing docs in v1. Atomic creation avoids data corruption.
- **Session-level context continuity.** Agno Team maintains history across turns (capped at 3 exchanges) so follow-up queries like *"now give me practice problems for that"* work correctly.
- **Never raises.** The `run_teaching_team()` interface always returns an `AgentResponse` — even on failure — so the UI never crashes from an unhandled exception.

---

## The Four Agents

### Agent Routing Rules

```
Query intent → Agent selected

EXPLAIN / TEACH / DESCRIBE / WHAT IS / HOW DOES  →  Professor
PLAN / ROADMAP / SCHEDULE / GUIDE / ADVISE        →  Advisor
FIND / RESEARCH / SOURCES / PAPERS / REFERENCES   →  Librarian
PRACTICE / QUIZ / TEST / EXERCISES / PROBLEMS     →  Teaching Assistant

Tie-break: ambiguous → default to Professor
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.11+ | Core development language |
| Agent Framework | Agno ≥ 1.0.0 | Agent and Team orchestration |
| LLM | OpenAI GPT-4o-mini | All agent reasoning and generation |
| Google Docs | Composio ≥ 0.5.0 | Create and return documents |
| Web Search | SerpAPI | Real-time web search for agents |
| UI | Streamlit ≥ 1.35.0 | Chat interface (Role 3) |
| Environment | python-dotenv | API key management |

---

## Team Structure

This project is built by three developers working independently:

| Role | Responsibility | Owns |
|------|---------------|------|
| **Role 1 — DevOps** | API keys, environment setup, Composio auth | `.env`, `composio add googledocs` |
| **Role 2 — Agent Logic** | All agent definitions, prompts, schemas, reasoning | `agents/`, `team/`, `schemas/`, `tools/`, `utils/` |
| **Role 3 — Full-stack** | Streamlit UI, session management, display | `ui/app.py` |

**Role 3 imports only one function:**
```python
from team.interface import run_teaching_team
```

---

## Project File Structure

```
ai_teaching_agent_team/
│
├── agents/                          # Role 2 — agent definitions
│   ├── __init__.py
│   ├── professor_agent.py           # Agent-01: lecture notes
│   ├── advisor_agent.py             # Agent-02: study plans
│   ├── librarian_agent.py           # Agent-03: research guides
│   └── teaching_assistant_agent.py  # Agent-04: practice sets
│
├── team/                            # Role 2 — orchestration
│   ├── __init__.py
│   ├── teaching_team.py             # Agno Team assembly + routing logic
│   └── interface.py                 # ⭐ ONLY file Role 3 imports
│
├── schemas/                         # Role 2 — shared data contracts
│   ├── __init__.py
│   └── agent_response.py            # AgentResponse dataclass
│
├── tools/                           # Role 2 — tool factories
│   ├── __init__.py
│   ├── composio_tools.py            # Google Docs tool factory
│   └── search_tools.py              # SerpAPI tool factory
│
├── utils/                           # Role 2 — helpers
│   ├── __init__.py
│   └── response_parser.py           # Raw Agno output → AgentResponse
│
├── tests/                           # Role 2 — test suite
│   ├── __init__.py
│   └── test_agents.py               # Routing + schema + integration tests
│
├── ui/                              # Role 3 — frontend
│   └── app.py                       # Streamlit chat application
│
├── test_smoke.py                    # Quick end-to-end sanity check
├── requirements.txt
├── .env                             # API keys — never commit this
├── .gitignore
└── README.md
```

---

## Prerequisites

Before starting, ensure you have:

- Python 3.11 or higher
- `pip` package manager
- API keys for: OpenAI, Composio, SerpAPI
- Composio Google Docs integration authenticated (done by Role 1)

To verify your Python version:
```bash
python --version
# Should output: Python 3.11.x or higher
```

---

## Installation & Setup

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-org/ai_teaching_agent_team.git
cd ai_teaching_agent_team
```

### Step 2 — Create and activate a virtual environment

```bash
python -m venv venv

# Mac / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

**Full `requirements.txt` contents:**
```
agno>=1.0.0
openai>=1.30.0
composio-agno>=0.5.0
google-auth>=2.28.0
google-auth-oauthlib>=1.2.0
google-api-python-client>=2.120.0
serpapi>=0.1.5
google-search-results>=2.4.2
streamlit>=1.35.0
python-dotenv>=1.0.0
pydantic>=2.0.0
requests>=2.31.0
pytest>=8.0.0
```

### Step 4 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values (see [Environment Configuration](#environment-configuration) below).

### Step 5 — Verify Composio Google Docs auth

This step must be completed by **Role 1 (DevOps)**. Confirm they have run:

```bash
composio add googledocs
```

And completed the OAuth browser flow for the target Google account. Without this, agents will generate content but fail to create documents.

---

## Environment Configuration

Create a `.env` file in the project root with these values:

```env
# Required
OPENAI_API_KEY=sk-proj-your-openai-key-here
COMPOSIO_API_KEY=your-composio-api-key-here
SERPAPI_API_KEY=your-serpapi-api-key-here

# Optional / defaults shown
OPENAI_MODEL=gpt-4o-mini
DEBUG=false
```

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API key for GPT-4o-mini |
| `COMPOSIO_API_KEY` | ✅ Yes | Composio key for Google Docs integration |
| `SERPAPI_API_KEY` | ✅ Yes | SerpAPI key for web search |
| `OPENAI_MODEL` | No | Defaults to `gpt-4o-mini` |
| `DEBUG` | No | Set to `true` to show tool call details in terminal |

> **Security:** The `.env` file is listed in `.gitignore` and must never be committed to version control.

---

## Running the App

### Quick smoke test (verify pipeline end-to-end)

```bash
python test_smoke.py
```

Expected output:
```
Running smoke test...

--- RESULTS ---
Agent:     professor
Success:   True
Doc URL:   https://docs.google.com/document/d/...
Doc Title: Lecture: Gradient Descent
Word Count: 847
Error:

Content preview (first 300 chars):
TITLE: Lecture: Gradient Descent
SECTION: Overview
Gradient descent is an optimization algorithm used to minimize a function...
```

### Run tests

```bash
python -m pytest tests/test_agents.py -v
```

### Launch the Streamlit UI

```bash
streamlit run ui/app.py
```

Then open `http://localhost:8501` in your browser.

---

## How It Works

### Request lifecycle

```
1. User types a query in the Streamlit chat input
2. UI calls run_teaching_team(topic, session_id, user_level)
3. interface.py validates input, calls teaching_team.run()
4. Agno Team (GPT-4o-mini, temp=0.1) reads routing rules
5. Team selects one agent and passes the query verbatim
6. Selected agent:
   a. Calls SerpAPI to search for relevant information (0-5 searches)
   b. Generates structured content following its format rules
   c. Calls GOOGLEDOCS_CREATE_DOCUMENT via Composio
   d. Composio creates the doc and returns a URL
   e. Agent includes DOC_URL: [url] in its response
7. response_parser.py extracts: agent ID, doc URL, doc title, content
8. AgentResponse object is returned to UI
9. UI displays: chat message + clickable Google Doc link
```

### Routing logic

The team coordinator uses keyword-based intent classification at `temperature=0.1` (near-deterministic). The routing instructions define priority ordering so ambiguous queries have consistent fallbacks.

### Session continuity

Each user session has a `session_id`. Agno Team stores up to 3 prior exchanges per session. This allows follow-up queries to work:

```
User: "Explain neural networks"
→ Professor Agent responds

User: "Now give me practice problems for that"
→ TA Agent sees prior context, generates neural network problems
```

---

## Agent Details

### Professor Agent

**ID:** `professor`  
**Persona:** Professor Nova  
**Trigger:** explain, teach, describe, what is, how does, overview

**Output document structure:**
```
TITLE: Lecture: [Topic Name]
SECTION: Overview          — 2-3 paragraphs, first-principles
SECTION: Core Concepts     — 5-8 bullet points, 2-3 sentences each
SECTION: Worked Example    — concrete step-by-step illustration
SECTION: Misconceptions    — 3 common mistakes with corrections
SECTION: Summary           — 3 sentences: what, why it matters, next step
```

**Tools used:** SerpAPI (1-2 searches for fact verification), Composio Google Docs  
**Target length:** 600–900 words  
**Model settings:** GPT-4o-mini, temperature 0.3, max_tokens 2048

---

### Academic Advisor Agent

**ID:** `advisor`  
**Persona:** Advisor Sage  
**Trigger:** plan, roadmap, schedule, guide me, how to learn, advise

**Output document structure:**
```
TITLE: Study Plan: [Topic Name]
SECTION: Goal Statement         — what the learner will achieve
SECTION: Prerequisites          — 3-5 prior knowledge areas
SECTION: Phase 1 - [Name]       — duration, objectives, resources, milestone
SECTION: Phase 2 - [Name]       — duration, objectives, resources, milestone
SECTION: Phase 3 - [Name]       — duration, objectives, resources, milestone
SECTION: Weekly Schedule        — sample 5-day week breakdown
SECTION: Success Metrics        — measurable mastery criteria
```

**Tools used:** SerpAPI (1-3 searches for resource discovery), Composio Google Docs  
**Target length:** 500–800 words  
**Model settings:** GPT-4o-mini, temperature 0.3, max_tokens 2048

> Note: Always states assumptions (e.g., "assumes 1 hour/day"). Never promises mastery in under 2 weeks for complex topics.

---

### Research Librarian Agent

**ID:** `librarian`  
**Persona:** Librarian Lumen  
**Trigger:** find, research, sources, papers, references, resources, bibliography

**Output document structure:**
```
TITLE: Research Guide: [Topic Name]
SECTION: Topic Brief              — 2 paragraphs on research scope
SECTION: Foundational Resources   — 3-4 books/papers + annotations
SECTION: Online Courses           — 3-4 links with descriptions
SECTION: Key Websites             — 3-4 trusted online resources
SECTION: Recent Developments      — 2-3 articles from 2022+
SECTION: Research Tips            — 3-4 search strategies
```

**Tools used:** SerpAPI (3-5 searches for resource discovery), Composio Google Docs  
**Target:** 8–14 total resources across all sections  
**Model settings:** GPT-4o-mini, temperature 0.3, max_tokens 2048

> Note: Never fabricates URLs. Paywalled resources are marked `[PAYWALLED]`. If a search returns no result for a resource, it is omitted rather than invented.

---

### Teaching Assistant Agent

**ID:** `ta`  
**Persona:** TA Atlas  
**Trigger:** practice, quiz, test me, problems, exercises, give me questions

**Output document structure:**
```
TITLE: Practice Set: [Topic Name]
SECTION: Topic Scope         — what skills the problems test
SECTION: Warm-Up Problems    — exactly 3 problems (foundational)
SECTION: Core Problems       — exactly 4 problems (intermediate)
SECTION: Challenge Problems  — exactly 2 problems (advanced)
SECTION: Solutions           — full worked solution for every problem
SECTION: Self-Assessment     — specific rubric to grade your own answers
```

**Tools used:** SerpAPI (0-1 searches for domain-specific facts), Composio Google Docs  
**Target:** exactly 9 problems (3+4+2), all with fully worked solutions  
**Model settings:** GPT-4o-mini, temperature 0.3, max_tokens 2048

---

## Output Schema

Every agent returns an `AgentResponse` object defined in `schemas/agent_response.py`:

```python
@dataclass
class AgentResponse:
    # Always populated
    agent: str       # 'professor' | 'advisor' | 'librarian' | 'ta' | 'unknown'
    topic: str       # Original user query
    content: str     # Full agent text (for chat display)
    doc_url: str     # Google Docs URL (empty string if creation failed)
    doc_title: str   # Document title
    success: bool    # False if any error occurred
    error: str       # Error message (empty string if success=True)

    # Metadata
    doc_id: str                # Google Doc ID
    search_queries: list       # SerpAPI queries used
    word_count: int            # Word count of content
    timestamp: str             # UTC ISO 8601 timestamp
```

**Serialization:**
```python
response.to_dict()   # → Python dict
response.to_json()   # → JSON string
```

**Error responses follow the same schema:**
```python
# On any failure, success=False and doc_url="" but content is still populated
AgentResponse.error_response(agent="unknown", topic=topic, error_msg="...")
```

---

## Integration Contract (for UI)

Role 3 imports and uses exactly this:

```python
from team.interface import run_teaching_team
from schemas.agent_response import AgentResponse
```

### Function signature

```python
def run_teaching_team(
    topic: str,            # User's question — 1 to 500 characters
    session_id: str,       # Unique session ID, e.g. UUID per user
    user_level: str,       # 'beginner' | 'intermediate' | 'advanced'
) -> AgentResponse:
    ...
```

### Usage example

```python
response = run_teaching_team(
    topic="Explain gradient descent",
    session_id="user-abc-123",
    user_level="intermediate"
)

# Display in chat
print(response.content)

# Render as clickable link
if response.success and response.doc_url:
    print(f"Open document: {response.doc_url}")
else:
    print(f"Document unavailable: {response.error}")

# Show which agent responded
print(f"Answered by: {response.agent}")
```

### UI responsibilities

- Validate that `response.success` is `True` before rendering `response.doc_url` as a link
- Handle `success=False` by showing `response.error` in a non-breaking error state
- Store `session_id` per user session (not per message) for context continuity
- Never call `teaching_team.run()` directly — only use `run_teaching_team()`

---

## Tool Integration

### Composio — Google Docs

- **Action used:** `GOOGLEDOCS_CREATE_DOCUMENT`
- **When:** Every successful agent run creates one new document
- **v1 policy:** Create only, never update (updates are v2 scope)
- **Auth requirement:** Role 1 must run `composio add googledocs` and complete OAuth before first use

Tool factory (`tools/composio_tools.py`):
```python
from composio_agno import ComposioToolSet, Action

def get_composio_tools() -> list:
    toolset = ComposioToolSet(api_key=os.getenv("COMPOSIO_API_KEY"))
    return toolset.get_tools(actions=[Action.GOOGLEDOCS_CREATE_DOCUMENT])
```

### SerpAPI — Web Search

- **Tool:** `SerpApiTools` from `agno.tools.serpapi`
- **Results per query:** 5 maximum (cost control)
- **Usage cap per request:** 0–5 searches depending on agent
- **Free tier:** 100 searches/month

Tool factory (`tools/search_tools.py`):
```python
from agno.tools.serpapi import SerpApiTools

def get_search_tools() -> SerpApiTools:
    return SerpApiTools(api_key=os.getenv("SERPAPI_API_KEY"), num_results=5)
```

### Error Handling

| Failure | Cause | Response |
|---------|-------|----------|
| Composio auth error | Invalid/expired key | `success=False`, content still returned |
| Google Doc creation fail | OAuth scope missing | Retry once, then content-only response |
| SerpAPI quota exceeded | 100/month limit | Agent proceeds using training knowledge |
| GPT-4o-mini timeout | Rate limit / network | Retry 3× with exponential backoff (2s, 4s, 8s) |
| Hallucinated URL | Model fabrication | Parser validates format; sets `doc_url=""` if invalid |
| Empty agent response | Model refusal | `error_response()` with descriptive message |
| Empty topic input | User error | Caught at `run_teaching_team()` before hitting model |

---

## Testing

### Run all tests

```bash
python -m pytest tests/test_agents.py -v
```

### Test coverage

| Test | What it checks |
|------|---------------|
| `test_response_schema` | `AgentResponse` fields are correct types and populated |
| `test_professor_routing` | Explanation queries → Professor Agent |
| `test_advisor_routing` | Planning queries → Advisor Agent |
| `test_librarian_routing` | Research queries → Librarian Agent |
| `test_ta_routing` | Practice queries → Teaching Assistant Agent |
| `test_empty_topic` | Empty string input is caught before model call |
| `test_doc_url_present` | Google Doc URL is returned and valid |

### Acceptance criteria

- Routing accuracy ≥ 85% across test cases
- Google Doc creation success rate ≥ 95%
- Schema compliance: 100% (AgentResponse always returned)
- No unhandled exceptions from `run_teaching_team()`

### Prompt tuning protocol

If routing accuracy drops below 85%:

1. Identify which queries are misrouted (look for `MISS:` in test output)
2. Change **one thing** in `team/teaching_team.py` routing instructions
3. Re-run tests and compare before/after accuracy
4. Log every change — never change multiple prompts in one iteration

---

## Cost & Token Budget

All agents use **GPT-4o-mini** at `temperature=0.3`.

| Component | Est. Tokens |
|-----------|-------------|
| System prompt (4 instruction blocks) | ~400 |
| User query + level prefix | ~50 |
| SerpAPI results injected | ~500 |
| Session history (3 turns max) | ~600 |
| **Total input per request** | **~1,550** |
| Agent output (600–900 word doc) | ~1,200 |
| **Total per request** | **~2,750** |

**Estimated cost:** ~$0.0004 per request  
**At 1,000 requests/month:** ~$0.40

GPT-4o-mini pricing (as of 2024): $0.15 per 1M input tokens, $0.60 per 1M output tokens.

---

## Known Limitations (v1)

| Limitation | Scope | Planned for |
|-----------|-------|-------------|
| One agent per query | No multi-agent collaboration | v2 |
| Create-only for Google Docs | No updating existing docs | v2 |
| English only | No multilingual support | v2 |
| Single-topic queries | No compound multi-topic queries | v2 |
| SerpAPI free tier (100/month) | Limited web searches | v2 (paid tier) |
| No user authentication | Single shared Composio account | v2 |
| Plain text documents | No rich formatting, tables, or images in docs | v2 |

---

## Contributing

This project uses a three-role development model. Before making changes:

- **Agents (`agents/`):** Changes require updating the corresponding test cases in `tests/test_agents.py`
- **Schema (`schemas/agent_response.py`):** Any field additions or renames must be communicated to Role 3 before merging
- **Interface (`team/interface.py`):** The function signature of `run_teaching_team()` is frozen for v1. Do not add required parameters without coordinating with Role 3
- **Tools (`tools/`):** Role 1 must be informed of any new tool dependencies that require API key setup

### Branch naming convention

```
role2/feature-name    # Role 2 work
role3/feature-name    # Role 3 work
fix/description       # Bug fixes
```

---

## License

MIT License. See `LICENSE` for details.

---

*Built by a three-person team using Agno framework, OpenAI GPT-4o-mini, Composio, and SerpAPI.*
