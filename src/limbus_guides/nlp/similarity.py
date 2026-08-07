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


def _freeze(identities: dict[str, dict]) -> tuple[tuple[str, str], ...]:
    """Hashable (slug, text) view of a roster — the cache key for encoding."""
    return tuple((slug, identities[slug].get("description_text", "")) for slug in identities)


@lru_cache(maxsize=4)
def _encode_corpus(
    corpus: tuple[tuple[str, str], ...], model_name: str
) -> tuple[list[str], np.ndarray]:
    """
    Encode a frozen corpus once per distinct roster.

    ``find_synergy_teammates`` runs per identity but always over the same roster, so
    without this cache a full pipeline pass re-encodes every identity N times
    (N**2 encodes for an N-identity roster). Keyed on the texts themselves, so an
    edited or extended roster re-encodes automatically.
    """
    slugs = [slug for slug, _ in corpus]
    texts = [text for _, text in corpus]
    embeddings = _get_model(model_name).encode(texts, convert_to_numpy=True)
    embeddings.setflags(write=False)  # shared across callers — do not mutate
    return slugs, embeddings


@lru_cache(maxsize=4)
def _similarity_matrix(
    corpus: tuple[tuple[str, str], ...], model_name: str
) -> tuple[list[str], np.ndarray]:
    slugs, embeddings = _encode_corpus(corpus, model_name)
    sim = cosine_similarity(embeddings)
    sim.setflags(write=False)  # shared across callers — do not mutate
    return slugs, sim


def clear_similarity_cache() -> None:
    """Drop cached embeddings — call after mutating identity text in-process."""
    _encode_corpus.cache_clear()
    _similarity_matrix.cache_clear()


def encode_identities(
    identities: dict[str, dict], model_name: str = DEFAULT_MODEL
) -> tuple[list[str], np.ndarray]:
    """Return (slugs, embeddings). The embedding array is read-only and cached."""
    return _encode_corpus(_freeze(identities), model_name)


def similarity_matrix(
    identities: dict[str, dict], model_name: str = DEFAULT_MODEL
) -> tuple[list[str], np.ndarray]:
    """Return (slugs, cosine similarity matrix). The matrix is read-only and cached."""
    return _similarity_matrix(_freeze(identities), model_name)


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
