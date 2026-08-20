"""Entity resolution básica entre fontes externas."""

from __future__ import annotations

import re
import unicodedata


def normalize_team_name(name: str) -> str:
    """Normaliza nome de time para comparação fuzzy."""
    text = unicodedata.normalize("NFKD", name)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"\b(fc|sc|ec|ac|cf|clube|club|de|do|da|dos|das)\b", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def token_set(name: str) -> set[str]:
    return set(normalize_team_name(name).split())


def similarity(a: str, b: str) -> float:
    """Jaccard sobre tokens — suficiente para spike Fase 0."""
    ta, tb = token_set(a), token_set(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def best_match(query: str, candidates: list[str], threshold: float = 0.55) -> tuple[str | None, float]:
    best_name: str | None = None
    best_score = 0.0
    for candidate in candidates:
        score = similarity(query, candidate)
        if score > best_score:
            best_score = score
            best_name = candidate
    if best_score < threshold:
        return None, best_score
    return best_name, best_score
