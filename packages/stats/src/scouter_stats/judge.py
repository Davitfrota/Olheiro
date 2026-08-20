"""Motor de julgamento Fase 0.5 — prior + odds → judgment → prediction.

Sem LLM. Context pack mínimo. ABSTAIN é saída de primeira classe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scouter_stats.models import RiskLabel, ValueDecision
from scouter_stats.risk import RiskInput, calibrate_risk
from scouter_stats.value import ValueGateInput, devig_multiplicative, evaluate_value_gate

PIPELINE_VERSION = "judge-v0.1"


def _load_env() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    env_path = repo_root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise SystemExit(f"Missing env var: {key}")
    return val


def _get_supabase():
    from supabase import create_client

    url = _env("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or _env("SUPABASE_ANON_KEY")
    return create_client(url, key)


@dataclass
class ContextPack:
    """Context pack mínimo — KNOWN/UNKNOWN explícitos."""

    lineup_status: str = "UNKNOWN"
    absences_known: bool = False
    high_absences: int = 0
    total_absences: int = 0
    has_prior: bool = False
    has_odds: bool = False
    thin_data: bool = False
    missing_fields: list[str] = field(default_factory=list)

    def completeness(self) -> float:
        score = 0.0
        if self.has_prior:
            score += 0.30
        if self.has_odds:
            score += 0.25
        if not self.thin_data:
            score += 0.15
        if self.lineup_status == "CONFIRMED":
            score += 0.20
        elif self.lineup_status == "PROBABLE":
            score += 0.10
        if self.absences_known:
            score += 0.10
        return round(min(1.0, score), 3)

    def context_hash(self) -> str:
        payload = {
            "lineup": self.lineup_status,
            "absences_known": self.absences_known,
            "high": self.high_absences,
            "total": self.total_absences,
            "missing": sorted(self.missing_fields),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


@dataclass
class JudgmentResult:
    match_id: str
    prior_id: str
    odds_snapshot_id: str | None
    market: str
    selection: str
    p_prior_selection: float
    p_adj: float
    se_adj: float
    p_fair: float
    edge: float
    value_decision: ValueDecision
    risk_label: RiskLabel | None
    prediction_status: str
    odds_hash: str
    context_hash: str
    cache_key: str
    veto_reasons: list[str]
    confidence_score: float
    value_reason: str
    completeness: float
    extracted_signals: list[dict] = field(default_factory=list)
    adjustments: dict = field(default_factory=dict)


def median_odds(outcome_maps: list[dict[str, float]]) -> dict[str, float]:
    keys = ("home", "draw", "away")
    out: dict[str, float] = {}
    for k in keys:
        vals = [m[k] for m in outcome_maps if k in m and m[k] and m[k] > 1]
        if not vals:
            raise ValueError(f"missing odds for {k}")
        out[k] = float(statistics.median(vals))
    return out


def build_context_pack(
    *,
    thin_data: bool,
    has_odds: bool,
    absences: list[dict] | None = None,
    lineup_status: str = "UNKNOWN",
) -> ContextPack:
    missing: list[str] = []
    if lineup_status == "UNKNOWN":
        missing.append("lineup")
    absences_known = absences is not None
    if not absences_known:
        missing.append("absences")
    high = 0
    total = 0
    if absences:
        total = len(absences)
        high = sum(1 for a in absences if a.get("importance") == "high")
    return ContextPack(
        lineup_status=lineup_status,
        absences_known=absences_known,
        high_absences=high,
        total_absences=total,
        has_prior=True,
        has_odds=has_odds,
        thin_data=thin_data,
        missing_fields=missing,
    )


def judge_h2h_selection(
    *,
    match_id: str,
    prior_id: str,
    selection: str,
    p_prior: dict[str, float],
    se_prior: dict[str, float],
    sample: dict[str, Any],
    odds_outcomes: dict[str, float],
    odds_hash: str,
    odds_snapshot_id: str | None,
    pack: ContextPack,
    lambda_home: float = 1.0,
) -> JudgmentResult:
    """Julga um selection 1x2. p_adj = p_prior (sem ajuste qualitativo ainda)."""
    p_fair_map = devig_multiplicative(odds_outcomes)
    p_adj = float(p_prior[selection])
    se_adj = float(se_prior.get(selection, se_prior.get("home", 0.08)))
    p_fair = float(p_fair_map[selection])
    thin = bool(sample.get("thin_data", False))
    completeness = pack.completeness()

    gate = evaluate_value_gate(
        ValueGateInput(
            p_adj=p_adj,
            se_adj=se_adj,
            p_fair=p_fair,
            information_completeness=completeness,
            thin_data=thin,
        )
    )

    risk = calibrate_risk(
        RiskInput(
            selection=selection,
            p_adj=p_adj,
            p_fair=p_fair,
            se_adj=se_adj,
            value_decision=gate.decision,
            information_completeness=completeness,
            thin_data=thin,
            lineup_status=pack.lineup_status,  # type: ignore[arg-type]
            high_absences=pack.high_absences,
            total_absences=pack.total_absences,
            abs_delta_lambda=0.0,
            lambda_prior=lambda_home,
        )
    )

    decision: ValueDecision = gate.decision
    if risk.force_abstain:
        decision = "ABSTAIN"
        status = "abstained"
    elif decision == "ABSTAIN":
        status = "abstained"
    else:
        status = "published"

    ctx_hash = pack.context_hash()
    cache_key = f"{match_id}:h2h:{selection}:{odds_hash}:{ctx_hash}"

    return JudgmentResult(
        match_id=match_id,
        prior_id=prior_id,
        odds_snapshot_id=odds_snapshot_id,
        market="h2h",
        selection=selection,
        p_prior_selection=round(p_adj, 4),
        p_adj=round(p_adj, 4),
        se_adj=round(se_adj, 4),
        p_fair=round(p_fair, 4),
        edge=gate.edge,
        value_decision=decision,
        risk_label=risk.risk_label if decision != "ABSTAIN" else None,
        prediction_status=status,
        odds_hash=odds_hash,
        context_hash=ctx_hash,
        cache_key=cache_key,
        veto_reasons=risk.veto_reasons,
        confidence_score=risk.confidence_score,
        value_reason=gate.reason,
        completeness=completeness,
        extracted_signals=[],
        adjustments={
            "delta_lambda": 0.0,
            "note": "phase-0.5 stats-only, no qualitative adjust",
            "value_reason": gate.reason,
        },
    )


def pick_match_tip(judgments: list[JudgmentResult]) -> JudgmentResult:
    """Escolhe o tip: VALUE; senão NOISE se modelo e mercado concordam no favorito; senão ABSTAIN."""
    values = [j for j in judgments if j.value_decision == "VALUE" and j.prediction_status == "published"]
    if values:
        return max(values, key=lambda j: j.edge)

    model_fav = max(judgments, key=lambda j: j.p_adj)
    market_fav = max(judgments, key=lambda j: j.p_fair)

    noises = [j for j in judgments if j.value_decision == "NOISE" and j.prediction_status == "published"]
    if model_fav.selection == market_fav.selection:
        agreed = [j for j in noises if j.selection == model_fav.selection]
        # Discordância forte de probabilidade (>8pp) sem contexto → não publicar tip
        publishable = [
            j for j in agreed
            if abs(j.p_adj - j.p_fair) <= 0.08 or j.completeness >= 0.7
        ]
        if publishable:
            return publishable[0]
        extra_veto = "edge_disagreement_without_context"
    else:
        extra_veto = "model_market_favorite_disagree"

    # ABSTAIN no favorito do modelo (não forçar tip)
    abstained = JudgmentResult(
        match_id=model_fav.match_id,
        prior_id=model_fav.prior_id,
        odds_snapshot_id=model_fav.odds_snapshot_id,
        market=model_fav.market,
        selection=model_fav.selection,
        p_prior_selection=model_fav.p_prior_selection,
        p_adj=model_fav.p_adj,
        se_adj=model_fav.se_adj,
        p_fair=model_fav.p_fair,
        edge=model_fav.edge,
        value_decision="ABSTAIN",
        risk_label=None,
        prediction_status="abstained",
        odds_hash=model_fav.odds_hash,
        context_hash=model_fav.context_hash,
        cache_key=model_fav.cache_key,
        veto_reasons=list(dict.fromkeys([*model_fav.veto_reasons, extra_veto])),
        confidence_score=0.0,
        value_reason=f"abstain: {extra_veto}",
        completeness=model_fav.completeness,
        extracted_signals=model_fav.extracted_signals,
        adjustments=model_fav.adjustments,
    )
    return abstained


def _hash_odds(outcomes: dict[str, float]) -> str:
    canonical = json.dumps({"market": "h2h", "line": None, "outcomes": outcomes}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def load_match_jobs(sb, *, limit: int | None = None) -> list[dict]:
    """Carrega matches com prior + odds agregadas (mediana por bookmaker)."""
    priors = sb.table("statistical_priors").select("*").execute().data
    if not priors:
        return []

    latest: dict[str, dict] = {}
    for p in priors:
        mid = p["match_id"]
        if mid not in latest or p["computed_at"] > latest[mid]["computed_at"]:
            latest[mid] = p

    odds = (
        sb.table("odds_snapshots")
        .select("id, match_id, outcomes, odds_hash, captured_at, bookmaker_id")
        .eq("market", "h2h")
        .execute()
        .data
    )
    by_match: dict[str, list[dict]] = {}
    for o in odds:
        by_match.setdefault(o["match_id"], []).append(o)

    jobs: list[dict] = []
    for mid, prior in latest.items():
        snaps = by_match.get(mid, [])
        if not snaps:
            continue
        snaps.sort(key=lambda x: x["captured_at"], reverse=True)
        latest_by_book: dict[str, dict] = {}
        for s in snaps:
            bid = s["bookmaker_id"]
            if bid not in latest_by_book:
                latest_by_book[bid] = s
        outcome_maps = [s["outcomes"] for s in latest_by_book.values()]
        try:
            med = median_odds(outcome_maps)
        except ValueError:
            continue
        jobs.append({
            "match_id": mid,
            "prior": prior,
            "odds_outcomes": med,
            "odds_hash": _hash_odds(med),
            "odds_snapshot_id": snaps[0]["id"],
        })
        if limit and len(jobs) >= limit:
            break
    return jobs


def persist_judgment(sb, tip: JudgmentResult, *, is_free_tier: bool = True) -> dict:
    """Upsert judgment + prediction no Supabase."""
    judgment_row = {
        "match_id": tip.match_id,
        "prior_id": tip.prior_id,
        "odds_snapshot_id": tip.odds_snapshot_id,
        "market": tip.market,
        "selection": tip.selection,
        "p_prior_selection": tip.p_prior_selection,
        "p_adj": tip.p_adj,
        "se_adj": tip.se_adj,
        "p_fair": tip.p_fair,
        "edge": tip.edge,
        "value_decision": tip.value_decision,
        "risk_label": tip.risk_label,
        "prediction_status": tip.prediction_status,
        "odds_hash": tip.odds_hash,
        "context_hash": tip.context_hash,
        "cache_key": tip.cache_key,
        "extracted_signals": tip.extracted_signals,
        "adjustments": tip.adjustments,
        "veto_reasons": tip.veto_reasons,
        "pipeline_version": PIPELINE_VERSION,
        "judged_at": datetime.now(timezone.utc).isoformat(),
    }

    existing = (
        sb.table("prediction_judgments")
        .select("id")
        .eq("cache_key", tip.cache_key)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        jid = existing[0]["id"]
        sb.table("prediction_judgments").update(judgment_row).eq("id", jid).execute()
    else:
        inserted = sb.table("prediction_judgments").insert(judgment_row).execute().data
        jid = inserted[0]["id"]

    pred = {
        "judgment_id": jid,
        "match_id": tip.match_id,
        "market": tip.market,
        "selection": tip.selection,
        "model_probability": tip.p_adj,
        "market_probability": tip.p_fair,
        "edge": tip.edge,
        "confidence_score": tip.confidence_score,
        "risk_label": tip.risk_label,
        "value_decision": tip.value_decision,
        "is_free_tier": is_free_tier,
        "explanation": None,
        "published_at": (
            datetime.now(timezone.utc).isoformat()
            if tip.prediction_status == "published"
            else None
        ),
    }

    pred_existing = (
        sb.table("predictions")
        .select("id")
        .eq("judgment_id", jid)
        .limit(1)
        .execute()
        .data
    )
    if pred_existing:
        sb.table("predictions").update(pred).eq("id", pred_existing[0]["id"]).execute()
    else:
        sb.table("predictions").insert(pred).execute()

    return {"judgment_id": jid, "status": tip.prediction_status, "decision": tip.value_decision}


def main() -> None:
    parser = argparse.ArgumentParser(description="Scouter judgment pipeline — prior+odds → predictions")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    _load_env()
    sb = _get_supabase()
    jobs = load_match_jobs(sb, limit=args.limit)

    published = abstained = value_n = noise_n = 0
    samples: list[dict] = []

    for job in jobs:
        prior = job["prior"]
        sample = prior.get("sample") or {}
        pack = build_context_pack(
            thin_data=bool(sample.get("thin_data", False)),
            has_odds=True,
            absences=None,
            lineup_status="UNKNOWN",
        )
        judgments = [
            judge_h2h_selection(
                match_id=job["match_id"],
                prior_id=prior["id"],
                selection=sel,
                p_prior=prior["p_prior"],
                se_prior=prior["se_prior"],
                sample=sample,
                odds_outcomes=job["odds_outcomes"],
                odds_hash=job["odds_hash"],
                odds_snapshot_id=job["odds_snapshot_id"],
                pack=pack,
                lambda_home=float(prior.get("lambda_home") or 1.0),
            )
            for sel in ("home", "draw", "away")
        ]
        tip = pick_match_tip(judgments)

        if tip.value_decision == "VALUE":
            value_n += 1
        elif tip.value_decision == "NOISE":
            noise_n += 1

        if tip.prediction_status == "published":
            published += 1
        else:
            abstained += 1

        if len(samples) < 8:
            samples.append({
                "match_id": tip.match_id[:8],
                "selection": tip.selection,
                "decision": tip.value_decision,
                "risk": tip.risk_label,
                "edge": tip.edge,
                "p_adj": tip.p_adj,
                "p_fair": tip.p_fair,
                "completeness": tip.completeness,
                "status": tip.prediction_status,
                "vetoes": tip.veto_reasons[:4],
            })

        if not args.dry_run:
            persist_judgment(sb, tip)

    print(json.dumps({
        "jobs": len(jobs),
        "published": published,
        "abstained": abstained,
        "value": value_n,
        "noise": noise_n,
        "dry_run": args.dry_run,
        "pipeline_version": PIPELINE_VERSION,
        "samples": samples,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
