"""Estágio 6 — calibração de risco com vetos duros.

Conservador ≠ favorito. Value bet nunca é conservador.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from scouter_stats.models import RiskLabel, ValueDecision

LineupStatus = Literal["UNKNOWN", "PROBABLE", "CONFIRMED"]

MARKET_DISAGREE_PP = 0.08  # 8 pp em 1x2


@dataclass
class RiskInput:
    selection: str
    p_adj: float
    p_fair: float
    se_adj: float
    value_decision: ValueDecision
    information_completeness: float
    thin_data: bool
    lineup_status: LineupStatus = "UNKNOWN"
    high_absences: int = 0
    total_absences: int = 0
    abs_delta_lambda: float = 0.0
    lambda_prior: float = 1.0


@dataclass
class RiskResult:
    risk_label: RiskLabel | None
    veto_reasons: list[str] = field(default_factory=list)
    force_abstain: bool = False
    confidence_score: float = 0.0


def _disagrees_market(p_adj: float, p_fair: float) -> bool:
    return abs(p_adj - p_fair) > MARKET_DISAGREE_PP


def calibrate_risk(inp: RiskInput) -> RiskResult:
    """Aplica regras + vetos. Nunca promove confiança cosmética."""
    vetos: list[str] = []
    force_abstain = False

    if inp.lineup_status == "UNKNOWN":
        vetos.append("lineup_unknown")

    if inp.lineup_status == "UNKNOWN" and inp.high_absences >= 2:
        vetos.append("unknown_lineup_with_high_absences")
        force_abstain = True

    if inp.total_absences >= 3:
        vetos.append("three_or_more_starters_out")

    if inp.thin_data:
        vetos.append("thin_data")

    if inp.information_completeness < 0.7:
        vetos.append("completeness_below_0.7")

    if _disagrees_market(inp.p_adj, inp.p_fair):
        vetos.append("disagrees_market_gt_8pp")

    if inp.value_decision == "VALUE":
        vetos.append("value_bet_not_conservative")

    if inp.abs_delta_lambda > 0.15:
        vetos.append("large_lambda_adjustment")

    # Self-distrust extremo: value com lineup UNKNOWN → abstain
    if inp.value_decision == "VALUE" and inp.lineup_status == "UNKNOWN":
        vetos.append("value_without_confirmed_lineup")
        force_abstain = True

    if force_abstain:
        return RiskResult(
            risk_label=None,
            veto_reasons=vetos,
            force_abstain=True,
            confidence_score=0.0,
        )

    # Score de robustez (0–1)
    incompleteness = 1.0 - inp.information_completeness
    lambda_pen = 0.0
    if inp.lambda_prior > 0:
        lambda_pen = min(0.4, inp.abs_delta_lambda / inp.lambda_prior)
    disagree = 1.0 if _disagrees_market(inp.p_adj, inp.p_fair) else 0.0
    robustness = max(
        0.0,
        1.0 - incompleteness - lambda_pen - (0.2 * disagree) - (0.15 if inp.thin_data else 0.0),
    )

    # Label base
    if inp.value_decision == "VALUE" or disagree or inp.abs_delta_lambda > 0.1:
        label: RiskLabel = "risky"
    elif robustness >= 0.75 and not vetos:
        label = "conservative"
    elif robustness >= 0.55:
        label = "moderate"
    else:
        label = "risky"

    # Vetos duros: nunca conservador se qualquer red flag
    hard_block_conservative = {
        "lineup_unknown",
        "unknown_lineup_with_high_absences",
        "three_or_more_starters_out",
        "thin_data",
        "completeness_below_0.7",
        "disagrees_market_gt_8pp",
        "value_bet_not_conservative",
        "large_lambda_adjustment",
        "value_without_confirmed_lineup",
    }
    if label == "conservative" and any(v in hard_block_conservative for v in vetos):
        label = "moderate" if "disagrees_market_gt_8pp" not in vetos else "risky"
        vetos.append("downgraded_from_conservative")

    return RiskResult(
        risk_label=label,
        veto_reasons=vetos,
        force_abstain=False,
        confidence_score=round(robustness, 4),
    )
