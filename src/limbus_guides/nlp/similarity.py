"""Identity similarity via sentence-transformers embeddings."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model(model_name: str = DEFAULT_MODEL):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def encode_identities(identities: dict[str, dict], model_name: str = DEFAULT_MODEL) -> tuple[list[str], np.ndarray]:
    slugs = list(identities.keys())
    texts = [identities[s].get("description_text", "") for s in slugs]
    model = _get_model(model_name)
    embeddings = model.encode(texts, convert_to_numpy=True)
    return slugs, embeddings


def similarity_matrix(identities: dict[str, dict], model_name: str = DEFAULT_MODEL) -> tuple[list[str], np.ndarray]:
    slugs, embeddings = encode_identities(identities, model_name)
    return slugs, cosine_similarity(embeddings)


def top_similar(
    slug: str,
    identities: dict[str, dict],
    k: int = 5,
    model_name: str = DEFAULT_MODEL,
    exclude_same_sinner: bool = True,
) -> list[tuple[str, float]]:
    slugs, sim = similarity_matrix(identities, model_name)
    if slug not in slugs:
        return []
    idx = slugs.index(slug)
    source_sinner = identities[slug].get("sinner")
    pairs = []
    for j, other in enumerate(slugs):
        if j == idx:
            continue
        if exclude_same_sinner and identities[other].get("sinner") == source_sinner:
            continue
        pairs.append((other, float(sim[idx][j])))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs[:k]
