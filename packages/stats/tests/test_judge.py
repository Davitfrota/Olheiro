"""Testes do calibrador de risco e do julgamento h2h."""

from scouter_stats.judge import (
    build_context_pack,
    judge_h2h_selection,
    median_odds,
    pick_match_tip,
)
from scouter_stats.risk import RiskInput, calibrate_risk
from scouter_stats.value import ValueGateInput, evaluate_value_gate


def test_never_conservative_with_unknown_lineup():
    result = calibrate_risk(
        RiskInput(
            selection="home",
            p_adj=0.55,
            p_fair=0.52,
            se_adj=0.06,
            value_decision="NOISE",
            information_completeness=0.85,
            thin_data=False,
            lineup_status="UNKNOWN",
        )
    )
    assert result.risk_label != "conservative"
    assert "lineup_unknown" in result.veto_reasons


def test_value_never_conservative():
    result = calibrate_risk(
        RiskInput(
            selection="home",
            p_adj=0.62,
            p_fair=0.48,
            se_adj=0.05,
            value_decision="VALUE",
            information_completeness=0.9,
            thin_data=False,
            lineup_status="CONFIRMED",
        )
    )
    assert result.risk_label == "risky"
    assert "value_bet_not_conservative" in result.veto_reasons


def test_value_with_unknown_lineup_forces_abstain():
    result = calibrate_risk(
        RiskInput(
            selection="home",
            p_adj=0.62,
            p_fair=0.48,
            se_adj=0.05,
            value_decision="VALUE",
            information_completeness=0.7,
            thin_data=False,
            lineup_status="UNKNOWN",
        )
    )
    assert result.force_abstain is True


def test_canonical_three_absences_blocks_conservative():
    result = calibrate_risk(
        RiskInput(
            selection="home",
            p_adj=0.72,
            p_fair=0.68,
            se_adj=0.06,
            value_decision="NOISE",
            information_completeness=0.9,
            thin_data=False,
            lineup_status="CONFIRMED",
            total_absences=3,
            high_absences=3,
        )
    )
    assert result.risk_label != "conservative"
    assert "three_or_more_starters_out" in result.veto_reasons


def test_low_completeness_allows_noise_not_value():
    noise = evaluate_value_gate(
        ValueGateInput(
            p_adj=0.52,
            se_adj=0.06,
            p_fair=0.50,
            information_completeness=0.55,
            thin_data=False,
        )
    )
    assert noise.decision == "NOISE"

    value_attempt = evaluate_value_gate(
        ValueGateInput(
            p_adj=0.70,
            se_adj=0.05,
            p_fair=0.50,
            information_completeness=0.55,
            thin_data=False,
        )
    )
    assert value_attempt.decision == "ABSTAIN"


def test_context_pack_completeness_stats_only():
    pack = build_context_pack(thin_data=False, has_odds=True, absences=None)
    assert pack.completeness() == 0.7
    assert "lineup" in pack.missing_fields


def test_judge_h2h_and_pick_tip():
    pack = build_context_pack(thin_data=False, has_odds=True)
    # Odds skewed so market favorite = home, model also home-leaning
    judgments = [
        judge_h2h_selection(
            match_id="m1",
            prior_id="p1",
            selection=sel,
            p_prior={"home": 0.50, "draw": 0.27, "away": 0.23},
            se_prior={"home": 0.07, "draw": 0.06, "away": 0.07},
            sample={"thin_data": False, "matches_home_season": 10, "matches_away_season": 10},
            odds_outcomes={"home": 1.90, "draw": 3.40, "away": 4.20},
            odds_hash="abc",
            odds_snapshot_id=None,
            pack=pack,
        )
        for sel in ("home", "draw", "away")
    ]
    tip = pick_match_tip(judgments)
    assert tip.selection == "home"
    assert tip.value_decision in {"VALUE", "NOISE", "ABSTAIN"}
    if tip.risk_label:
        assert tip.risk_label != "conservative"


def test_pick_tip_abstains_when_favorites_disagree():
    pack = build_context_pack(thin_data=False, has_odds=True)
    judgments = [
        judge_h2h_selection(
            match_id="m2",
            prior_id="p2",
            selection=sel,
            p_prior={"home": 0.55, "draw": 0.25, "away": 0.20},
            se_prior={"home": 0.07, "draw": 0.06, "away": 0.07},
            sample={"thin_data": False},
            # Market strongly favors away
            odds_outcomes={"home": 3.80, "draw": 3.40, "away": 1.85},
            odds_hash="xyz",
            odds_snapshot_id=None,
            pack=pack,
        )
        for sel in ("home", "draw", "away")
    ]
    tip = pick_match_tip(judgments)
    assert tip.value_decision == "ABSTAIN"
    assert "model_market_favorite_disagree" in tip.veto_reasons


def test_median_odds():
    med = median_odds([
        {"home": 2.0, "draw": 3.0, "away": 4.0},
        {"home": 2.2, "draw": 3.2, "away": 3.8},
        {"home": 2.1, "draw": 3.1, "away": 3.9},
    ])
    assert med["home"] == 2.1
