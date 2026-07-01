"""TF-IDF keyword extraction for dominant mechanics per identity."""

from __future__ import annotations

from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer


def extract_keywords(identities: dict[str, dict], top_k: int = 8) -> dict[str, list[str]]:
    slugs = list(identities.keys())
    texts = [identities[s].get("description_text", "") for s in slugs]
    if not any(texts):
        return {s: [] for s in slugs}

    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[A-Za-z][A-Za-z0-9:+']+\b",
    )
    matrix = vectorizer.fit_transform(texts)
    features = vectorizer.get_feature_names_out()

    result: dict[str, list[str]] = {}
    for i, slug in enumerate(slugs):
        row = matrix[i].toarray().flatten()
        top_idx = row.argsort()[-top_k:][::-1]
        result[slug] = [features[j] for j in top_idx if row[j] > 0]
    return result


def dominant_mechanics_from_profile(mechanic_profile: dict) -> list[str]:
    counts = mechanic_profile.get("all_mechanics", {})
    if isinstance(counts, dict):
        return [m for m, _ in Counter(counts).most_common(5)]
    return mechanic_profile.get("primary_mechanics", [])
