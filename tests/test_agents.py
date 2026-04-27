"""
Run these BEFORE handing off to Role 3.
Command: python -m pytest tests/ -v
"""
from team.interface import run_teaching_team
from schemas.agent_response import AgentResponse


# ── TEST 1: Schema compliance ──────────────────────────────────
def test_response_schema():
    response = run_teaching_team("Explain what machine learning is")
    assert isinstance(response, AgentResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 50
    assert response.agent in ["professor", "advisor", "librarian", "ta", "unknown"]
    assert isinstance(response.success, bool)
    assert isinstance(response.doc_url, str)
    print(f"PASS: Schema test | Agent: {response.agent}")


# ── TEST 2: Professor routing ──────────────────────────────────
def test_professor_routing():
    queries = [
        "Explain how neural networks work",
        "What is gradient descent?",
        "Teach me about recursion",
    ]
    for q in queries:
        r = run_teaching_team(q)
        assert r.agent == "professor", f"Expected professor, got {r.agent} for: '{q}'"
        print(f"PASS: Professor routing | Query: '{q}'")


# ── TEST 3: Advisor routing ────────────────────────────────────
def test_advisor_routing():
    queries = [
        "Create a 3-month plan to learn Python",
        "Give me a study roadmap for machine learning",
    ]
    for q in queries:
        r = run_teaching_team(q)
        assert r.agent == "advisor", f"Expected advisor, got {r.agent} for: '{q}'"
        print(f"PASS: Advisor routing | Query: '{q}'")


# ── TEST 4: Librarian routing ──────────────────────────────────
def test_librarian_routing():
    queries = [
        "Find me the best resources for learning SQL",
        "List papers and sources on transformers",
    ]
    for q in queries:
        r = run_teaching_team(q)
        assert r.agent == "librarian", f"Expected librarian, got {r.agent} for: '{q}'"
        print(f"PASS: Librarian routing | Query: '{q}'")


# ── TEST 5: TA routing ─────────────────────────────────────────
def test_ta_routing():
    queries = [
        "Give me practice problems on binary search",
        "Quiz me on Big O notation",
    ]
    for q in queries:
        r = run_teaching_team(q)
        assert r.agent == "ta", f"Expected ta, got {r.agent} for: '{q}'"
        print(f"PASS: TA routing | Query: '{q}'")


# ── TEST 6: Empty topic guard ──────────────────────────────────
def test_empty_topic():
    r = run_teaching_team("")
    assert r.success == False
    assert "empty" in r.error.lower()
    print("PASS: Empty topic guard")


# ── TEST 7: Google Doc URL present ────────────────────────────
def test_doc_url_present():
    r = run_teaching_team("Explain what an API is")
    if r.success:
        assert r.doc_url.startswith("https://docs.google.com"), \
            f"Bad URL: {r.doc_url}"
        print(f"PASS: Doc URL present | URL: {r.doc_url}")
    else:
        print(f"WARN: Doc URL missing | Error: {r.error}")