"""
utils/prereq_gate.py — Prolog-Powered Prerequisite Gating

Before an agent processes an advanced topic, this module:
1. Detects which Prolog topic atom(s) the query maps to.
2. Queries the prerequisite_chain/2 facts for missing prereqs.
3. Returns a GateResult — either cleared (proceed) or blocked (warn the user).

The UI consumes GateResult to optionally show a warning and prereq tree
before running the agent. The gate is purely advisory — it never hard-blocks.

Public API:
    check_topic_gate(topic_str) -> GateResult
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Data class
# --------------------------------------------------------------------------

@dataclass
class GateResult:
    topic_str: str                        # original user query
    detected_atom: str                    # matched Prolog atom (e.g. "deep_learning")
    detected_label: str                   # human name (e.g. "Deep Learning")
    all_prerequisites: list[str]          # all transitive prereqs (Prolog atoms)
    prerequisite_labels: list[str]        # human-readable prereq names
    is_advanced: bool                     # True if difficulty == advanced
    difficulty: str                       # "beginner" | "intermediate" | "advanced" | "unknown"
    gate_cleared: bool                    # True → no warning needed
    warning_message: str                  # populated when gate_cleared is False
    prereq_tree: dict                     # atom -> list[direct prereqs] for tree rendering


def _atom_to_label(atom: str) -> str:
    return atom.replace("_", " ").title()


def _get_difficulty(atom: str) -> str:
    """Query Prolog for topic_difficulty/2. Returns 'unknown' on failure."""
    try:
        from utils.prolog_engine import _prolog, PROLOG_AVAILABLE
        if not PROLOG_AVAILABLE or _prolog is None:
            return "unknown"
        results = list(_prolog.query(f"topic_difficulty({atom}, Level)"))
        if results:
            return str(results[0]["Level"])
    except Exception:
        pass
    return "unknown"


def _build_prereq_tree(atom: str) -> dict:
    """
    Return a dict mapping each topic → its DIRECT prerequisites,
    for all topics in the prerequisite chain of *atom*.
    Used by the UI to render a visual tree.
    """
    tree: dict = {}
    try:
        from utils.prolog_engine import _prolog, PROLOG_AVAILABLE
        if not PROLOG_AVAILABLE or _prolog is None:
            return tree

        # Get full transitive chain
        chain_results = list(_prolog.query(f"prerequisite_chain(X, {atom})"))
        involved = {str(r["X"]) for r in chain_results}
        involved.add(atom)

        # For each involved topic, get its DIRECT prerequisites
        for t in involved:
            direct = list(_prolog.query(f"prerequisite(X, {t})"))
            direct_atoms = [str(r["X"]) for r in direct]
            # Only keep edges that are within the chain (prune irrelevant nodes)
            tree[t] = [d for d in direct_atoms if d in involved]

    except Exception as exc:
        logger.debug("_build_prereq_tree error: %s", exc)
    return tree


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def check_topic_gate(topic_str: str) -> GateResult:
    """
    Analyse topic_str against the Prolog knowledge base.

    Returns a GateResult — always succeeds (gate_cleared=True on any error).
    """
    _EMPTY = GateResult(
        topic_str=topic_str,
        detected_atom="",
        detected_label="",
        all_prerequisites=[],
        prerequisite_labels=[],
        is_advanced=False,
        difficulty="unknown",
        gate_cleared=True,
        warning_message="",
        prereq_tree={},
    )

    try:
        from utils.prolog_engine import PROLOG_AVAILABLE, TOPIC_ALIASES, get_prerequisites
        if not PROLOG_AVAILABLE:
            return _EMPTY

        # 1. Match topic string → Prolog atom
        topic_lower = topic_str.lower()
        matched_atom = ""
        for atom, aliases in TOPIC_ALIASES.items():
            if any(alias in topic_lower for alias in aliases):
                matched_atom = atom
                break

        if not matched_atom:
            return _EMPTY

        # 2. Fetch prerequisites
        prereqs = get_prerequisites(matched_atom)   # transitive, deduplicated
        difficulty = _get_difficulty(matched_atom)
        is_advanced = difficulty == "advanced"

        # 3. Build warning if topic is non-trivial and has prerequisites
        prereq_labels = [_atom_to_label(p) for p in prereqs]
        gate_cleared = not prereqs or difficulty == "beginner"

        warning = ""
        if not gate_cleared:
            prereq_str = ", ".join(prereq_labels[:6])
            extra = f" and {len(prereq_labels) - 6} more" if len(prereq_labels) > 6 else ""
            warning = (
                f"**{_atom_to_label(matched_atom)}** is a **{difficulty}** topic. "
                f"It builds on: {prereq_str}{extra}. "
                f"Make sure you're comfortable with those first — or dive in anyway!"
            )

        tree = _build_prereq_tree(matched_atom) if not gate_cleared else {}

        return GateResult(
            topic_str=topic_str,
            detected_atom=matched_atom,
            detected_label=_atom_to_label(matched_atom),
            all_prerequisites=prereqs,
            prerequisite_labels=prereq_labels,
            is_advanced=is_advanced,
            difficulty=difficulty,
            gate_cleared=gate_cleared,
            warning_message=warning,
            prereq_tree=tree,
        )

    except Exception as exc:
        logger.warning("check_topic_gate error (%s) — gate cleared by default.", exc)
        return _EMPTY
