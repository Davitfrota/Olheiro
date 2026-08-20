"""Modelo Poisson para prior de 1x2 e mercados derivados."""

from __future__ import annotations

import math
from dataclasses import dataclass

from scouter_stats.models import (
    DerivedProbabilities,
    LambdaPair,
    PriorProbabilities,
    SampleInfo,
    StandardErrors,
    StatisticalPrior,
)


@dataclass(frozen=True)
class TeamStrength:
    attack: float
    defense: float


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def score_matrix(lambda_home: float, lambda_away: float, max_goals: int = 10) -> list[list[float]]:
    """Matriz P(home=i, away=j) assumindo Poisson independente."""
    home_probs = [_poisson_pmf(i, lambda_home) for i in range(max_goals + 1)]
    away_probs = [_poisson_pmf(j, lambda_away) for j in range(max_goals + 1)]
    tail_home = max(0.0, 1.0 - sum(home_probs))
    tail_away = max(0.0, 1.0 - sum(away_probs))
    home_probs[-1] += tail_home
    away_probs[-1] += tail_away

    return [
        [home_probs[i] * away_probs[j] for j in range(max_goals + 1)]
        for i in range(max_goals + 1)
    ]


def h2h_from_matrix(matrix: list[list[float]]) -> PriorProbabilities:
    p_home = p_draw = p_away = 0.0
    for i, row in enumerate(matrix):
        for j, p in enumerate(row):
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
    return PriorProbabilities(home=p_home, draw=p_draw, away=p_away)


def over_25_from_matrix(matrix: list[list[float]]) -> float:
    total = 0.0
    for i, row in enumerate(matrix):
        for j, p in enumerate(row):
            if i + j >= 3:
                total += p
    return total


def btts_from_matrix(matrix: list[list[float]]) -> float:
    return sum(
        p
        for i, row in enumerate(matrix)
        for j, p in enumerate(row)
        if i >= 1 and j >= 1
    )


def estimate_lambda(
    home: TeamStrength,
    away: TeamStrength,
    league_avg_goals: float = 1.35,
    home_advantage: float = 1.10,
) -> LambdaPair:
    """λ_home e λ_away a partir de forças de ataque/defesa normalizadas."""
    lambda_home = league_avg_goals * home.attack * away.defense * home_advantage
    lambda_away = league_avg_goals * away.attack * home.defense
    return LambdaPair(home=round(lambda_home, 4), away=round(lambda_away, 4))


def estimate_se(
    sample: SampleInfo,
    base_se: float = 0.06,
) -> StandardErrors:
    """Heurística Fase 0 — substituída por bootstrap no backtest."""
    penalty = 0.0
    if sample.thin_data:
        penalty += 0.04
    min_matches = min(sample.matches_home_season, sample.matches_away_season)
    if min_matches < 8:
        penalty += 0.03
    elif min_matches < 12:
        penalty += 0.015

    se = base_se + penalty
    return StandardErrors(home=se, draw=se * 0.9, away=se)


def build_prior(
    match_id: str,
    home: TeamStrength,
    away: TeamStrength,
    matches_home_season: int,
    matches_away_season: int,
    calibration_bucket: str = "brasileirao-1x2",
    league_avg_goals: float = 1.35,
    home_advantage: float = 1.10,
) -> StatisticalPrior:
    thin_data = matches_home_season < 8 or matches_away_season < 8
    sample = SampleInfo(
        matches_home_season=matches_home_season,
        matches_away_season=matches_away_season,
        thin_data=thin_data,
    )

    lambdas = estimate_lambda(
        home,
        away,
        league_avg_goals=league_avg_goals,
        home_advantage=home_advantage,
    )
    matrix = score_matrix(lambdas.home, lambdas.away)
    h2h = h2h_from_matrix(matrix)

    return StatisticalPrior(
        match_id=match_id,
        sample=sample,
        **{"lambda": lambdas},
        p_prior=h2h,
        derived=DerivedProbabilities(
            over_25=round(over_25_from_matrix(matrix), 4),
            btts=round(btts_from_matrix(matrix), 4),
        ),
        se_prior=estimate_se(sample),
        calibration_bucket=calibration_bucket,
    )
