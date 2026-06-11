"""
S2-01 — Sri Lankan GCE O/L Mathematics topic taxonomy (NIE syllabus, Grades 10–11).

Single source of truth for topic classification across the pipeline:
  - question extraction (ai/extract.py) classifies each question to a canonical topic
  - blueprint slots (ai/schemas.py) reference canonical topics
  - retrieval (app/services/retrieval.py) filters the question bank by topic
  - StyleProfile (app/services/style.py) aggregates the teacher's topic_distribution

Topic strings stored in the DB are the canonical `.value` of `Topic`. Free-text topic
labels coming from the model are normalised to a canonical topic via `normalize_topic`.
"""

from __future__ import annotations

from enum import Enum


class Topic(str, Enum):
    """Canonical O/L Mathematics topics. The string value is what is persisted."""

    NUMBER = "Number"
    ALGEBRA = "Algebra"
    INDICES_LOGARITHMS = "Indices and Logarithms"
    SETS_PROBABILITY = "Sets and Probability"
    GEOMETRY = "Geometry"
    MENSURATION = "Mensuration"
    TRIGONOMETRY = "Trigonometry"
    STATISTICS = "Statistics"
    FUNCTIONS_GRAPHS = "Functions and Graphs"
    MATRICES = "Matrices"
    VECTORS = "Vectors"
    CONSTRUCTIONS = "Constructions"
    COMMERCIAL_MATH = "Commercial Mathematics"


# Representative subtopics per topic. Used to guide extraction and as a controlled
# vocabulary for StyleProfile; not exhaustive — extraction may add free-text subtopics.
SUBTOPICS: dict[Topic, list[str]] = {
    Topic.NUMBER: [
        "Real numbers", "Number patterns", "Surds", "Scientific notation",
        "Ratio and proportion", "Percentages", "Fractions and decimals",
    ],
    Topic.ALGEBRA: [
        "Algebraic expressions", "Factorisation", "Algebraic fractions", "Formulae",
        "Linear equations", "Simultaneous equations", "Quadratic equations", "Inequalities",
    ],
    Topic.INDICES_LOGARITHMS: ["Laws of indices", "Logarithms", "Log tables"],
    Topic.SETS_PROBABILITY: [
        "Set notation", "Venn diagrams", "Set operations", "Probability of events",
    ],
    Topic.GEOMETRY: [
        "Angles", "Parallel lines", "Triangles", "Polygons", "Pythagoras' theorem",
        "Circle theorems", "Loci", "Congruence and similarity",
    ],
    Topic.MENSURATION: [
        "Perimeter", "Area", "Surface area", "Volume", "Arc length and sector area",
    ],
    Topic.TRIGONOMETRY: [
        "Trigonometric ratios", "Heights and distances", "Angles of elevation and depression",
    ],
    Topic.STATISTICS: [
        "Data representation", "Frequency distributions", "Mean median mode",
        "Histograms", "Cumulative frequency",
    ],
    Topic.FUNCTIONS_GRAPHS: [
        "Cartesian plane", "Linear graphs", "Gradient", "Quadratic functions and graphs",
    ],
    Topic.MATRICES: ["Matrix operations", "Matrix multiplication", "Order of a matrix"],
    Topic.VECTORS: ["Vector notation", "Vector addition", "Scalar multiplication", "Position vectors"],
    Topic.CONSTRUCTIONS: ["Ruler and compass constructions", "Bisectors", "Loci constructions"],
    Topic.COMMERCIAL_MATH: ["Simple interest", "Compound interest", "Taxes", "Banking", "Profit and loss"],
}

# Common surface variants the model may emit, mapped to canonical topics.
_ALIASES: dict[str, Topic] = {
    "numbers": Topic.NUMBER,
    "real numbers": Topic.NUMBER,
    "arithmetic": Topic.NUMBER,
    "indices": Topic.INDICES_LOGARITHMS,
    "logarithms": Topic.INDICES_LOGARITHMS,
    "logs": Topic.INDICES_LOGARITHMS,
    "sets": Topic.SETS_PROBABILITY,
    "probability": Topic.SETS_PROBABILITY,
    "set theory": Topic.SETS_PROBABILITY,
    "geometry and constructions": Topic.GEOMETRY,
    "circle theorems": Topic.GEOMETRY,
    "circles": Topic.GEOMETRY,
    "trigonometry": Topic.TRIGONOMETRY,
    "trig": Topic.TRIGONOMETRY,
    "mensuration": Topic.MENSURATION,
    "area and volume": Topic.MENSURATION,
    "perimeter area volume": Topic.MENSURATION,
    "statistics": Topic.STATISTICS,
    "data": Topic.STATISTICS,
    "graphs": Topic.FUNCTIONS_GRAPHS,
    "functions": Topic.FUNCTIONS_GRAPHS,
    "coordinate geometry": Topic.FUNCTIONS_GRAPHS,
    "matrix": Topic.MATRICES,
    "matrices": Topic.MATRICES,
    "vectors": Topic.VECTORS,
    "constructions": Topic.CONSTRUCTIONS,
    "commercial maths": Topic.COMMERCIAL_MATH,
    "commercial mathematics": Topic.COMMERCIAL_MATH,
    "financial mathematics": Topic.COMMERCIAL_MATH,
    "interest": Topic.COMMERCIAL_MATH,
}


def all_topics() -> list[str]:
    """Canonical topic strings — for prompts and UI dropdowns."""
    return [t.value for t in Topic]


def is_canonical(topic: str) -> bool:
    return topic in {t.value for t in Topic}


def normalize_topic(raw: str) -> Topic:
    """Map a free-text topic label to a canonical Topic.

    Tries exact canonical match, then alias table, then substring containment.
    Falls back to Topic.NUMBER (the broadest bucket) so classification never crashes
    the pipeline — extraction logs the original label in `subtopics` for review.
    """
    if not raw:
        return Topic.NUMBER
    cleaned = raw.strip()
    for t in Topic:
        if cleaned.lower() == t.value.lower():
            return t
    key = cleaned.lower()
    if key in _ALIASES:
        return _ALIASES[key]
    for alias, topic in _ALIASES.items():
        if alias in key or key in alias:
            return topic
    for t in Topic:
        if t.value.lower() in key or key in t.value.lower():
            return t
    return Topic.NUMBER


def taxonomy_for_prompt() -> str:
    """Render the taxonomy as a compact block for inclusion in extraction prompts."""
    lines = ["Canonical O/L Mathematics topics (classify each question to exactly one):"]
    for t in Topic:
        subs = ", ".join(SUBTOPICS.get(t, []))
        lines.append(f"  - {t.value}: {subs}")
    return "\n".join(lines)
