"""
Prolog Engine — Lightweight Python ↔ SWI-Prolog bridge.

Provides:
  Static helpers  (prompt-time):  get_prerequisites(), get_validation_rules()
  Runtime helpers (post-LLM):     validate_advisor_plan(), validate_ta_solutions()

SAFETY CONTRACT:
  • Every public function is wrapped in try/except.
  • If pyswip, SWI-Prolog, or the knowledge base is missing → functions
    return safe defaults and the system continues exactly as before.
"""

import os
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Safe Prolog initialisation
# ---------------------------------------------------------------------------

PROLOG_AVAILABLE = False
_prolog = None

try:
    from pyswip import Prolog

    _prolog = Prolog()

    # Resolve path to knowledge_base.pl (project_root/prolog/knowledge_base.pl)
    _KB_PATH = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "prolog", "knowledge_base.pl")
    )
    # SWI-Prolog on Windows needs forward slashes
    _KB_PATH = _KB_PATH.replace("\\", "/")

    if os.path.isfile(_KB_PATH):
        _prolog.consult(_KB_PATH)
        PROLOG_AVAILABLE = True
        logger.info("Prolog engine initialised — knowledge base loaded.")
    else:
        logger.warning("knowledge_base.pl not found at %s — Prolog disabled.", _KB_PATH)
        _prolog = None

except Exception as exc:
    logger.warning("Prolog unavailable (%s). System will continue without it.", exc)
    _prolog = None

# ---------------------------------------------------------------------------
# Topic-name normalisation
# ---------------------------------------------------------------------------

# Maps natural-language variants → Prolog atom names
TOPIC_ALIASES: dict[str, list[str]] = {
    "algebra":                       ["algebra", "algebraic"],
    "calculus":                      ["calculus", "differential calculus", "integral calculus"],
    "linear_algebra":                ["linear algebra", "matrices", "vectors", "matrix"],
    "statistics":                    ["statistics", "statistical"],
    "probability":                   ["probability", "probabilistic"],
    "machine_learning":              ["machine learning", "ml ", "supervised learning", "unsupervised learning"],
    "deep_learning":                 ["deep learning", "neural network", "neural networks", "cnn", "rnn"],
    "data_structures":               ["data structures", "data structure", "linked list", "binary tree", "hash table"],
    "algorithms":                    ["algorithms", "algorithm", "sorting", "searching"],
    "programming_basics":            ["programming basics", "programming fundamentals", "basic programming",
                                      "python basics", "intro to programming", "introduction to programming"],
    "databases":                     ["databases", "database", "sql", "relational database"],
    "web_development":               ["web development", "web dev", "html", "css", "javascript"],
    "dynamic_programming":           ["dynamic programming"],
    "object_oriented_programming":   ["object oriented", "oop", "object-oriented"],
    "discrete_mathematics":          ["discrete mathematics", "discrete math"],
    "logic":                         ["logic", "propositional logic", "predicate logic", "boolean logic"],
    "differential_equations":        ["differential equations", "ode", "pde"],
    "data_science":                  ["data science", "data analysis"],
}

# Maps Prolog valid_answer_type step atoms → human-readable descriptions
_STEP_LABELS: dict[str, str] = {
    "show_differentiation":      "show differentiation steps",
    "show_integration":          "show integration steps",
    "verify_boundary_conditions":"verify boundary conditions",
    "isolate_variables":         "isolate variables",
    "simplify_equations":        "simplify equations",
    "apply_formula":             "apply statistical formulas",
    "interpret_results":         "interpret results",
    "explain_logic":             "explain code logic",
    "analyze_complexity":        "analyze time/space complexity",
    "justify_model_selection":   "justify model selection",
    "define_evaluation_metrics": "define evaluation metrics",
    "draw_free_body_diagram":    "draw free-body diagram",
    "verify_units":              "verify units",
    "explain_structure_choice":  "explain data-structure choice",
    "show_step_trace":           "show step-by-step trace",
    "prove_correctness":         "prove correctness",
}

# Keywords used to detect problem domains in TA output
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "calculus":          ["calculus", "derivative", "integral", "differentiation", "integration", "limit"],
    "algebra":           ["algebra", "equation", "variable", "polynomial", "quadratic"],
    "statistics":        ["statistics", "mean", "variance", "standard deviation", "hypothesis", "regression"],
    "programming":       ["programming", "code", "function", "loop", "array", "recursion"],
    "machine_learning":  ["machine learning", "model", "training", "classification", "regression", "overfitting"],
    "physics":           ["physics", "force", "velocity", "acceleration", "energy", "momentum"],
    "data_structures":   ["data structure", "linked list", "tree", "graph", "stack", "queue"],
    "algorithms":        ["algorithm", "sorting", "searching", "divide and conquer", "greedy"],
}


# =========================================================================
# 1.  LOW-LEVEL PROLOG QUERIES
# =========================================================================

def check_prerequisite(topic_a: str, topic_b: str) -> bool:
    """
    Return True if *topic_a* is a (transitive) prerequisite of *topic_b*.
    Returns False on any failure — ensures no false-positive violations.
    """
    if not PROLOG_AVAILABLE or _prolog is None:
        return False
    try:
        results = list(_prolog.query(f"prerequisite_chain({topic_a}, {topic_b})"))
        return len(results) > 0
    except Exception:
        return False


def validate_answer(question_type: str, answer_keywords: list[str]) -> bool:
    """
    Return True if *answer_keywords* satisfy all expected steps for
    *question_type* according to valid_answer_type/2 rules.
    Returns True (optimistic) on any failure.
    """
    if not PROLOG_AVAILABLE or _prolog is None:
        return True
    try:
        results = list(_prolog.query(f"valid_answer_type({question_type}, Step)"))
        expected_steps = {str(r["Step"]) for r in results}
        if not expected_steps:
            return True
        return all(
            any(kw in _STEP_LABELS.get(step, step) for kw in answer_keywords)
            for step in expected_steps
        )
    except Exception:
        return True


def get_prerequisites(topic: str) -> list[str]:
    """Return all (transitive) prerequisites for *topic*. Empty list on failure."""
    if not PROLOG_AVAILABLE or _prolog is None:
        return []
    try:
        results = list(_prolog.query(f"prerequisite_chain(X, {topic})"))
        return list({str(r["X"]) for r in results})
    except Exception:
        return []


def get_validation_rules() -> list[str]:
    """Return human-readable validation rules for prompt enrichment."""
    if not PROLOG_AVAILABLE or _prolog is None:
        return []
    try:
        results = list(_prolog.query("valid_answer_type(Type, Step)"))
        rules = []
        seen = set()
        for r in results:
            ptype = str(r["Type"])
            step = str(r["Step"])
            label = _STEP_LABELS.get(step, step.replace("_", " "))
            entry = f"For {ptype} problems: {label}"
            if entry not in seen:
                seen.add(entry)
                rules.append(entry)
        return rules
    except Exception:
        return []


# =========================================================================
# 2.  INTERNAL HELPERS  (used by runtime validators)
# =========================================================================

def _extract_topics_by_section(content: str) -> list[tuple[int, str]]:
    """
    Return (section_index, prolog_atom) pairs for topics found in the plan.

    Splits content on 'SECTION:' boundaries.  Section 0 (title area) is skipped.
    Topics within the same section are considered unordered peers — only
    cross-section ordering is meaningful for prerequisite validation.
    """
    sections = content.lower().split("section:")
    # sections[0] is everything before the first SECTION: (title) — skip it
    results: list[tuple[int, str]] = []
    seen: set[str] = set()

    for sec_idx, section_text in enumerate(sections[1:], start=1):
        for prolog_name, aliases in TOPIC_ALIASES.items():
            if prolog_name in seen:
                continue
            for alias in aliases:
                if alias in section_text:
                    results.append((sec_idx, prolog_name))
                    seen.add(prolog_name)
                    break
    return results


def _detect_problem_types(content: str) -> list[str]:
    """Detect which problem domains appear in *content*."""
    content_lower = content.lower()
    types: list[str] = []
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in content_lower for kw in keywords):
            types.append(domain)
    return types


def _human_topic(prolog_atom: str) -> str:
    """Convert a Prolog atom like 'linear_algebra' → 'Linear Algebra'."""
    return prolog_atom.replace("_", " ").title()


# =========================================================================
# 3.  RUNTIME VALIDATION  (called from team/interface.py)
# =========================================================================

def _is_direct_prerequisite(topic_a: str, topic_b: str) -> bool:
    """Return True if topic_a is a DIRECT (non-transitive) prerequisite of topic_b.
    Uses prerequisite/2, not prerequisite_chain/2, to avoid cascade noise."""
    if not PROLOG_AVAILABLE or _prolog is None:
        return False
    try:
        results = list(_prolog.query(f"prerequisite({topic_a}, {topic_b})"))
        return len(results) > 0
    except Exception:
        return False


# Maximum number of prerequisite notes to append (keeps output readable)
_MAX_PREREQ_NOTES = 5


def validate_advisor_plan(content: str, topic: str) -> str:
    """
    Post-LLM validation for the Academic Advisor.

    Checks whether the generated study plan respects prerequisite ordering.
    Uses DIRECT prerequisites only (not transitive chains) to avoid noise.
    Compares topics ACROSS sections only — within-section order is ignored.
    If violations are detected, appends correction notes (max 5) to the content.
    Returns the ORIGINAL content unchanged on any failure.
    """
    if not PROLOG_AVAILABLE or _prolog is None:
        return content

    try:
        section_topics = _extract_topics_by_section(content)
        if len(section_topics) < 2:
            return content                      # Not enough topics to validate

        # Check cross-section pairs: if a topic in a later section is a
        # DIRECT prerequisite of a topic in an earlier section, that's a violation.
        violations: list[tuple[str, str]] = []  # (should_be_first, should_be_second)
        for i in range(len(section_topics)):
            for j in range(i + 1, len(section_topics)):
                sec_i, topic_i = section_topics[i]
                sec_j, topic_j = section_topics[j]
                if sec_i == sec_j:
                    continue                    # Same section — order doesn't matter
                # topic_i is in an earlier section than topic_j.
                # Violation if topic_j is a direct prerequisite of topic_i.
                if _is_direct_prerequisite(topic_j, topic_i):
                    violations.append((topic_j, topic_i))

        if not violations:
            return content                      # Ordering is correct

        # Build correction notes (capped for readability)
        notes: list[str] = [
            "",
            "--- Prerequisite Validation Notes ---",
        ]
        for prereq, advanced in violations[:_MAX_PREREQ_NOTES]:
            notes.append(
                f"NOTE: Based on prerequisite validation, "
                f"you should learn {_human_topic(prereq)} before {_human_topic(advanced)}."
            )
        if len(violations) > _MAX_PREREQ_NOTES:
            notes.append(f"... and {len(violations) - _MAX_PREREQ_NOTES} more ordering suggestion(s).")

        logger.info("Advisor plan: %d prerequisite ordering issue(s) detected.", len(violations))
        return content + "\n".join(notes)

    except Exception as exc:
        logger.warning("Advisor Prolog validation failed (%s) — returning original content.", exc)
        return content


def validate_ta_solutions(content: str) -> str:
    """
    Post-LLM validation for the Teaching Assistant.

    Checks whether generated solutions contain the expected logical
    components for the detected problem domain.
    Returns the ORIGINAL content unchanged on any failure.
    """
    if not PROLOG_AVAILABLE or _prolog is None:
        return content

    try:
        problem_types = _detect_problem_types(content)
        if not problem_types:
            return content                      # Domain not recognised

        # Locate the solutions section (solutions come after problems)
        content_lower = content.lower()
        sol_start = content_lower.find("solution")
        if sol_start == -1:
            return content                      # No solutions section found
        solutions_text = content_lower[sol_start:]

        # For each detected domain, query expected steps and check presence
        missing_steps: list[str] = []
        for ptype in problem_types:
            try:
                results = list(_prolog.query(f"valid_answer_type({ptype}, Step)"))
            except Exception:
                continue
            for r in results:
                step_atom = str(r["Step"])
                label = _STEP_LABELS.get(step_atom, step_atom.replace("_", " "))
                # Check if the human-readable label (or its keywords) appear
                # anywhere in the solutions text
                step_words = label.lower().split()
                if not any(word in solutions_text for word in step_words if len(word) > 3):
                    missing_steps.append(label)

        if not missing_steps:
            return content                      # All expected steps present

        # De-duplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for s in missing_steps:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        notes = [
            "",
            "--- Solution Validation Notes ---",
            "NOTE: Solution may be incomplete. Expected steps include:",
        ]
        for step in unique:
            notes.append(f"  - {step}")

        logger.info("TA solutions: %d expected step(s) not explicitly found.", len(unique))
        return content + "\n".join(notes)

    except Exception as exc:
        logger.warning("TA Prolog validation failed (%s) — returning original content.", exc)
        return content
