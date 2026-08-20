"""Backtest Fase 0 — Brier score do prior Poisson vs resultados reais."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass

import httpx

from scouter_stats.poisson import TeamStrength, build_prior
from scouter_stats.spike import _load_env_file


@dataclass
class FixtureResult:
    fixture_id: str
    home: str
    away: str
    home_goals: int
    away_goals: int
    match_id: str | None = None  # UUID no Supabase, quando disponível


def fetch_finished_fixtures(
    client: httpx.Client,
    api_key: str,
    *,
    league_id: int = 71,
    season: int = 2024,
    max_fixtures: int = 60,
) -> list[FixtureResult]:
    """Busca fixtures finalizados — compatível com plano free."""
    response = client.get(
        "https://v3.football.api-sports.io/fixtures",
        headers={"x-apisports-key": api_key},
        params={"league": league_id, "season": season, "status": "FT"},
        timeout=60.0,
    )
    response.raise_for_status()
    rows = response.json().get("response", [])[:max_fixtures]

    return [
        FixtureResult(
            fixture_id=str(row["fixture"]["id"]),
            home=row["teams"]["home"]["name"],
            away=row["teams"]["away"]["name"],
            home_goals=row["goals"]["home"] or 0,
            away_goals=row["goals"]["away"] or 0,
        )
        for row in rows
    ]


def fetch_fixtures_from_supabase(*, max_fixtures: int | None = None) -> list[FixtureResult]:
    """Carrega matches finalizados do Supabase, ordenados por kickoff."""
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_ANON_KEY required for --source supabase")

    sb = create_client(url, key)
    query = (
        sb.table("matches")
        .select("id, kickoff_at, home_score, away_score, home_team:teams!matches_home_team_id_fkey(name), away_team:teams!matches_away_team_id_fkey(name)")
        .eq("status", "finished")
        .order("kickoff_at")
    )
    if max_fixtures:
        query = query.limit(max_fixtures)

    rows = query.execute().data or []
    fixtures: list[FixtureResult] = []
    for row in rows:
        home = row.get("home_team") or {}
        away = row.get("away_team") or {}
        fixtures.append(
            FixtureResult(
                fixture_id=row["id"],
                match_id=row["id"],
                home=home.get("name", "?"),
                away=away.get("name", "?"),
                home_goals=row.get("home_score") or 0,
                away_goals=row.get("away_score") or 0,
            )
        )
    return fixtures


def actual_outcome(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def brier_score(probs: dict[str, float], outcome: str) -> float:
    return sum((probs[k] - (1.0 if k == outcome else 0.0)) ** 2 for k in ("home", "draw", "away"))


def league_context(history: list[FixtureResult]) -> tuple[float, float]:
    """Retorna (gols médios por time, vantagem de casa) a partir do histórico."""
    if not history:
        return 1.35, 1.10

    home_goals = sum(fx.home_goals for fx in history)
    away_goals = sum(fx.away_goals for fx in history)
    games = max(1, len(history))

    avg_home = home_goals / games
    avg_away = away_goals / games
    avg_total_per_team = (avg_home + avg_away) / 2
    home_adv = avg_home / avg_away if avg_away > 0 else 1.10
    home_adv = min(1.25, max(1.0, home_adv))
    return max(0.9, min(1.8, avg_total_per_team)), home_adv


def rolling_strengths(
    fixtures: list[FixtureResult],
    idx: int,
    *,
    window: int = 10,
    default_attack: float = 1.0,
    default_defense: float = 1.0,
) -> tuple[TeamStrength, TeamStrength]:
    """Força simplificada com média de gols nos últimos N jogos por time."""
    history = fixtures[:idx]
    home_name = fixtures[idx].home
    away_name = fixtures[idx].away
    league_avg, _ = league_context(history)

    def team_rates(team: str) -> TeamStrength:
        scored: list[int] = []
        conceded: list[int] = []
        team_history_count = 0
        for fx in reversed(history):
            if fx.home == team:
                scored.append(fx.home_goals)
                conceded.append(fx.away_goals)
                team_history_count += 1
            elif fx.away == team:
                scored.append(fx.away_goals)
                conceded.append(fx.home_goals)
                team_history_count += 1
            if team_history_count >= window:
                break

        if not scored:
            return TeamStrength(default_attack, default_defense)

        # Smoothing para evitar extremos com pouca amostra.
        prior_weight = 4
        smoothed_scored = (sum(scored) + prior_weight * league_avg) / (len(scored) + prior_weight)
        smoothed_conceded = (sum(conceded) + prior_weight * league_avg) / (len(conceded) + prior_weight)

        avg_scored = sum(scored) / len(scored)
        avg_conceded = sum(conceded) / len(conceded)
        attack = ((0.4 * avg_scored) + (0.6 * smoothed_scored)) / league_avg
        defense = ((0.4 * avg_conceded) + (0.6 * smoothed_conceded)) / league_avg

        return TeamStrength(
            attack=max(0.6, min(1.6, attack)),
            defense=max(0.6, min(1.6, defense)),
        )

    return team_rates(home_name), team_rates(away_name)


def run_backtest(
    fixtures: list[FixtureResult],
    *,
    min_history: int = 8,
    collect_priors: bool = False,
) -> dict:
    scores: list[float] = []
    used = 0
    correct = 0
    outcome_counts = {"home": 0, "draw": 0, "away": 0}
    pred_counts = {"home": 0, "draw": 0, "away": 0}
    prior_rows: list[dict] = []

    for idx in range(min_history, len(fixtures)):
        history = fixtures[:idx]
        league_avg_goals, home_advantage = league_context(history)
        home_strength, away_strength = rolling_strengths(fixtures, idx)
        home_matches = sum(
            1 for fx in history if fx.home == fixtures[idx].home or fx.away == fixtures[idx].home
        )
        away_matches = sum(
            1 for fx in history if fx.home == fixtures[idx].away or fx.away == fixtures[idx].away
        )
        prior = build_prior(
            match_id=str(fixtures[idx].fixture_id),
            home=home_strength,
            away=away_strength,
            matches_home_season=home_matches,
            matches_away_season=away_matches,
            calibration_bucket="brasileirao-1x2-backtest",
            league_avg_goals=league_avg_goals,
            home_advantage=home_advantage,
        )
        probs = prior.p_prior.model_dump()
        outcome = actual_outcome(fixtures[idx].home_goals, fixtures[idx].away_goals)
        predicted = max(probs, key=probs.get)
        scores.append(brier_score(probs, outcome))
        outcome_counts[outcome] += 1
        pred_counts[predicted] += 1
        if predicted == outcome:
            correct += 1
        used += 1

        if collect_priors and fixtures[idx].match_id:
            prior_rows.append(
                {
                    "match_id": fixtures[idx].match_id,
                    "model_version": "poisson-dc-v0.1",
                    "calibration_bucket": "brasileirao-1x2-backtest",
                    "lambda_home": float(prior.lambda_.home),
                    "lambda_away": float(prior.lambda_.away),
                    "p_prior": probs,
                    "derived": prior.derived.model_dump(),
                    "se_prior": prior.se_prior.model_dump(),
                    "sample": prior.sample.model_dump(),
                    "already_in_model": ["rolling_attack", "rolling_defense", "home_advantage"],
                }
            )

    avg_brier = sum(scores) / len(scores) if scores else None
    accuracy = correct / used if used else None
    result = {
        "fixtures_total": len(fixtures),
        "fixtures_scored": used,
        "avg_brier_score": round(avg_brier, 4) if avg_brier is not None else None,
        "accuracy_argmax": round(accuracy, 4) if accuracy is not None else None,
        "baseline_brier_uniform": round(2 / 3, 4),
        "outcome_distribution": outcome_counts,
        "prediction_distribution": pred_counts,
        "beats_uniform": bool(avg_brier is not None and avg_brier < (2 / 3)),
        "note": "Brier < 0.667 indica prior melhor que chute uniforme (33/33/33).",
    }
    if collect_priors:
        result["_prior_rows"] = prior_rows
    return result


def persist_priors(prior_rows: list[dict]) -> dict:
    """Upsert statistical_priors no Supabase."""
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL/ANON_KEY required for --persist")

    sb = create_client(url, key)
    inserted = 0
    errors: list[str] = []

    # Batch em chunks de 50
    chunk_size = 50
    for i in range(0, len(prior_rows), chunk_size):
        chunk = prior_rows[i : i + chunk_size]
        try:
            sb.table("statistical_priors").upsert(
                chunk,
                on_conflict="match_id,model_version",
            ).execute()
            inserted += len(chunk)
        except Exception as exc:  # noqa: BLE001
            # Fallback row-by-row
            for row in chunk:
                try:
                    sb.table("statistical_priors").upsert(
                        row,
                        on_conflict="match_id,model_version",
                    ).execute()
                    inserted += 1
                except Exception as row_exc:  # noqa: BLE001
                    errors.append(str(row_exc)[:160])

    return {"persisted": inserted, "errors": errors[:5]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest Poisson prior — Brasileirão")
    parser.add_argument("--source", choices=["api", "supabase"], default="supabase")
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--max-fixtures", type=int, default=0, help="0 = todos")
    parser.add_argument("--min-history", type=int, default=8)
    parser.add_argument("--persist", action="store_true", help="Grava priors no Supabase")
    args = parser.parse_args()

    _load_env_file()
    max_fixtures = args.max_fixtures or None

    if args.source == "supabase":
        fixtures = fetch_fixtures_from_supabase(max_fixtures=max_fixtures)
    else:
        api_key = os.environ.get("API_FOOTBALL_KEY")
        if not api_key:
            print(json.dumps({"error": "API_FOOTBALL_KEY not set"}, ensure_ascii=False))
            sys.exit(2)
        with httpx.Client() as client:
            fixtures = fetch_finished_fixtures(
                client,
                api_key,
                season=args.season,
                max_fixtures=max_fixtures or 380,
            )

    result = run_backtest(
        fixtures,
        min_history=args.min_history,
        collect_priors=args.persist,
    )
    result["source"] = args.source
    result["season"] = args.season

    if args.persist:
        prior_rows = result.pop("_prior_rows", [])
        result["persist"] = persist_priors(prior_rows)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
