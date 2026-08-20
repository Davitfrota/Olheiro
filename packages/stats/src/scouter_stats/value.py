"""Estágio 5 — value bet: sinal vs ruído vs abstenção."""

from __future__ import annotations

from scouter_stats.models import ValueGateInput, ValueGateResult


def evaluate_value_gate(inp: ValueGateInput) -> ValueGateResult:
    edge = round(inp.p_adj - inp.p_fair, 4)

    if inp.information_completeness < inp.completeness_threshold:
        return ValueGateResult(
            edge=edge,
            decision="ABSTAIN",
            reason=f"completeness {inp.information_completeness:.2f} < {inp.completeness_threshold}",
        )

    if inp.thin_data and abs(edge) < inp.k_multiplier * inp.se_adj * 1.5:
        return ValueGateResult(
            edge=edge,
            decision="ABSTAIN",
            reason="thin_data with insufficient edge margin",
        )

    threshold = inp.k_multiplier * inp.se_adj
    if abs(edge) <= threshold:
        return ValueGateResult(
            edge=edge,
            decision="NOISE",
            reason=f"|edge| {abs(edge):.4f} <= k*se_adj ({threshold:.4f})",
        )

    if edge > threshold:
        return ValueGateResult(
            edge=edge,
            decision="VALUE",
            reason=f"positive edge {edge:.4f} > {threshold:.4f}",
        )

    return ValueGateResult(
        edge=edge,
        decision="ABSTAIN",
        reason=f"negative edge against market without structural override",
    )


def devig_multiplicative(outcomes: dict[str, float]) -> dict[str, float]:
    """Remove overround multiplicativo. outcomes: nome -> odd decimal."""
    implied = {k: 1.0 / v for k, v in outcomes.items() if v > 0}
    total = sum(implied.values())
    if total <= 0:
        raise ValueError("invalid odds")
    return {k: round(v / total, 4) for k, v in implied.items()}
