"""Testes do motor estatístico Fase 0."""

from scouter_stats.models import ValueGateInput
from scouter_stats.poisson import TeamStrength, build_prior
from scouter_stats.value import devig_multiplicative, evaluate_value_gate


def test_build_prior_probabilities_sum_to_one():
    prior = build_prior(
        match_id="test-match",
        home=TeamStrength(attack=1.2, defense=0.9),
        away=TeamStrength(attack=0.8, defense=1.1),
        matches_home_season=15,
        matches_away_season=14,
    )
    total = prior.p_prior.home + prior.p_prior.draw + prior.p_prior.away
    assert abs(total - 1.0) < 0.001
    assert prior.derived.over_25 is not None
    assert 0 < prior.derived.over_25 < 1


def test_value_gate_abstains_on_low_completeness_with_large_edge():
    # Completeness baixa + edge grande ⇒ ABSTAIN (não inventa VALUE)
    result = evaluate_value_gate(
        ValueGateInput(
            p_adj=0.72,
            se_adj=0.05,
            p_fair=0.50,
            information_completeness=0.55,
            thin_data=True,
        )
    )
    assert result.decision == "ABSTAIN"


def test_value_gate_noise_when_edge_within_se():
    result = evaluate_value_gate(
        ValueGateInput(
            p_adj=0.52,
            se_adj=0.06,
            p_fair=0.50,
            information_completeness=0.85,
            thin_data=False,
        )
    )
    assert result.decision == "NOISE"


def test_devig_multiplicative():
    fair = devig_multiplicative({"home": 1.40, "draw": 4.60, "away": 8.50})
    assert abs(sum(fair.values()) - 1.0) < 0.001
    raw_implied_home = 1 / 1.40
    assert fair["home"] < raw_implied_home  # overround removido reduz prob do favorito
