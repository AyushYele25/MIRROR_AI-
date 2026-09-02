"""Developer clustering using K-Means and HDBSCAN.

Groups developers into engineering archetype clusters based on their
fingerprint vectors. Also provides PCA/UMAP dimensionality reduction
for 2D profile visualization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ClusterResult:
    """Result of clustering a set of developer profiles."""
    cluster_labels: List[int] = field(default_factory=list)
    cluster_names: Dict[int, str] = field(default_factory=dict)
    cluster_centers: List[List[float]] = field(default_factory=list)
    n_clusters: int = 0
    silhouette_score: float = 0.0
    # 2D projection for visualization
    projection_2d: List[Tuple[float, float]] = field(default_factory=list)
    projection_method: str = "pca"


# ── Archetype naming ────────────────────────────────────────────

DIMENSION_NAMES = [
    "code_quality", "testing", "architecture", "documentation",
    "iteration", "debugging", "tooling", "ml_workflow", "project_complexity",
]

ARCHETYPE_TEMPLATES = {
    "code_quality": "Code Craftsman",
    "testing": "Quality Guardian",
    "architecture": "System Architect",
    "documentation": "Documentation Champion",
    "iteration": "Rapid Iterater",
    "debugging": "Bug Hunter",
    "tooling": "DevOps Engineer",
    "ml_workflow": "ML Practitioner",
    "project_complexity": "Scale Builder",
}


def _name_cluster(center: np.ndarray) -> str:
    """Generate a human-readable archetype name from cluster center."""
    if len(center) != len(DIMENSION_NAMES):
        return "General Developer"

    # Find the top 2 strongest dimensions
    indexed = list(enumerate(center))
    indexed.sort(key=lambda x: x[1], reverse=True)

    top_dims = [DIMENSION_NAMES[idx] for idx, _ in indexed[:2]]
    primary = ARCHETYPE_TEMPLATES.get(top_dims[0], "Developer")
    secondary = top_dims[1].replace("_", " ").title()

    return f"{primary} ({secondary})"


def cluster_profiles(
    vectors: List[List[float]],
    *,
    method: str = "kmeans",
    n_clusters: int | None = None,
    min_cluster_size: int = 3,
) -> ClusterResult:
    """Cluster developer profiles into engineering archetypes.

    Args:
        vectors: List of developer fingerprint vectors (9 dimensions).
        method: "kmeans" or "hdbscan".
        n_clusters: Number of clusters for K-Means (auto if None).
        min_cluster_size: Minimum cluster size for HDBSCAN.

    Returns:
        ClusterResult with labels, names, centers, and 2D projection.
    """
    result = ClusterResult()

    if len(vectors) < 2:
        result.cluster_labels = [0] * len(vectors)
        result.n_clusters = 1
        if vectors:
            result.cluster_names = {0: "Solo Profile"}
        return result

    X = np.array(vectors, dtype=np.float64)

    # Standardize for clustering
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ── Clustering ───────────────────────────────────────────────
    if method == "hdbscan" and len(vectors) >= min_cluster_size * 2:
        try:
            from hdbscan import HDBSCAN
            clusterer = HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=2,
                metric="euclidean",
            )
            labels = clusterer.fit_predict(X_scaled)
        except ImportError:
            logger.warning("hdbscan_not_available, falling back to kmeans")
            method = "kmeans"

    if method == "kmeans":
        from sklearn.cluster import KMeans

        if n_clusters is None:
            # Auto-select k using elbow heuristic (max 6 clusters)
            max_k = min(6, len(vectors) // 2, len(vectors))
            max_k = max(2, max_k)

            best_k = 2
            best_inertia_ratio = float("inf")

            for k in range(2, max_k + 1):
                km = KMeans(n_clusters=k, random_state=42, n_init=10)
                km.fit(X_scaled)
                if k > 2:
                    ratio = km.inertia_ / prev_inertia if prev_inertia > 0 else 1
                    if ratio < best_inertia_ratio:
                        best_inertia_ratio = ratio
                        best_k = k
                prev_inertia = km.inertia_

            n_clusters = best_k

        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)

        # Get centers in original scale
        centers_original = scaler.inverse_transform(km.cluster_centers_)
        result.cluster_centers = centers_original.tolist()

    result.cluster_labels = labels.tolist()
    result.n_clusters = len(set(labels) - {-1})

    # ── Silhouette score ─────────────────────────────────────────
    if result.n_clusters >= 2:
        from sklearn.metrics import silhouette_score
        valid_mask = np.array(labels) >= 0
        if valid_mask.sum() >= 2:
            result.silhouette_score = float(
                silhouette_score(X_scaled[valid_mask], np.array(labels)[valid_mask])
            )

    # ── Name clusters ────────────────────────────────────────────
    if result.cluster_centers:
        for i, center in enumerate(result.cluster_centers):
            result.cluster_names[i] = _name_cluster(np.array(center))
    else:
        # Compute centers from data for naming
        for label in set(labels):
            if label < 0:
                continue
            mask = np.array(labels) == label
            center = X[mask].mean(axis=0)
            result.cluster_names[label] = _name_cluster(center)

    # ── 2D Projection (PCA) ─────────────────────────────────────
    try:
        from sklearn.decomposition import PCA
        pca = PCA(n_components=2, random_state=42)
        coords = pca.fit_transform(X_scaled)
        result.projection_2d = [(float(x), float(y)) for x, y in coords]
        result.projection_method = "pca"
    except Exception as e:
        logger.debug("pca_projection_failed", error=str(e))

    logger.info(
        "clustering_complete",
        method=method,
        n_profiles=len(vectors),
        n_clusters=result.n_clusters,
        silhouette=result.silhouette_score,
    )

    return result
