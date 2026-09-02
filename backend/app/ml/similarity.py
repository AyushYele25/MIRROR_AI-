"""Profile similarity — cosine similarity and nearest-profile search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SimilarProfile:
    """A profile similar to the query."""
    index: int
    username: str
    similarity: float  # 0-1, higher = more similar
    shared_strengths: List[str]


DIMENSION_NAMES = [
    "code_quality", "testing", "architecture", "documentation",
    "iteration", "debugging", "tooling", "ml_workflow", "project_complexity",
]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    va = np.array(a, dtype=np.float64)
    vb = np.array(b, dtype=np.float64)

    dot = np.dot(va, vb)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot / (norm_a * norm_b))


def find_similar_profiles(
    query_vector: List[float],
    candidate_vectors: List[List[float]],
    candidate_usernames: List[str],
    *,
    top_k: int = 5,
    min_similarity: float = 0.3,
) -> List[SimilarProfile]:
    """Find the most similar developer profiles to a query.

    Args:
        query_vector: The 9-dimension fingerprint to compare.
        candidate_vectors: All other fingerprint vectors.
        candidate_usernames: Usernames corresponding to candidate vectors.
        top_k: Maximum number of similar profiles to return.
        min_similarity: Minimum cosine similarity threshold.

    Returns:
        List of SimilarProfile objects, sorted by similarity descending.
    """
    if not candidate_vectors:
        return []

    results = []
    for i, (candidate, username) in enumerate(
        zip(candidate_vectors, candidate_usernames)
    ):
        sim = cosine_similarity(query_vector, candidate)

        if sim < min_similarity:
            continue

        # Find shared strengths (dimensions where both are above 60)
        shared = []
        for j, dim in enumerate(DIMENSION_NAMES):
            if j < len(query_vector) and j < len(candidate):
                if query_vector[j] > 60 and candidate[j] > 60:
                    shared.append(dim.replace("_", " ").title())

        results.append(SimilarProfile(
            index=i,
            username=username,
            similarity=round(sim, 4),
            shared_strengths=shared,
        ))

    results.sort(key=lambda r: r.similarity, reverse=True)
    return results[:top_k]


def compute_similarity_matrix(
    vectors: List[List[float]],
) -> List[List[float]]:
    """Compute pairwise cosine similarity matrix.

    Returns an NxN matrix where entry [i][j] is the cosine similarity
    between profiles i and j.
    """
    if not vectors:
        return []

    X = np.array(vectors, dtype=np.float64)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    X_norm = X / norms

    sim_matrix = (X_norm @ X_norm.T).tolist()
    return [[round(v, 4) for v in row] for row in sim_matrix]
