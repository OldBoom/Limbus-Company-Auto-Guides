"""Canonical Limbus sinner roster order (Sinner #1–#12)."""

from __future__ import annotations

# In-game order. Used by the dashboard grid and config rebuild.
SINNER_ORDER = [
    "Yi Sang",
    "Faust",
    "Don Quixote",
    "Ryōshū",
    "Meursault",
    "Hong Lu",
    "Heathcliff",
    "Ishmael",
    "Rodion",
    "Sinclair",
    "Outis",
    "Gregor",
]


def sinner_sort_key(name: str) -> tuple[int, int | str]:
    """Sort key for canonical Limbus sinner order; unknowns go last A–Z."""
    try:
        return (0, SINNER_ORDER.index(name))
    except ValueError:
        return (1, name)
