"""Testes de matching entre fontes."""

from scouter_stats.matching import best_match, normalize_team_name, similarity


def test_normalize_team_name():
    assert normalize_team_name("São Paulo FC") == "sao paulo"
    assert normalize_team_name("Flamengo") == "flamengo"


def test_similarity_partial_match():
    score = similarity("Flamengo", "CR Flamengo")
    assert score >= 0.5


def test_best_match_above_threshold():
    match, score = best_match("Palmeiras", ["SE Palmeiras", "Flamengo"], threshold=0.4)
    assert match == "SE Palmeiras"
    assert score > 0.4
