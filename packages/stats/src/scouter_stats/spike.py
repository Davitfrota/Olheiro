"""Spike Fase 0 — valida conectividade e limites das APIs externas."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from scouter_stats.matching import best_match

# Plano free API-Football: temporadas 2022–2024, sem parâmetros next/last.
FREE_PLAN_SEASONS = (2024, 2023, 2022)
BRAZIL_LEAGUE_ID = 71
BRAZIL_ODDS_SPORT = "soccer_brazil_campeonato"


def _load_env_file() -> None:
    """Carrega .env da raiz do repositório no ambiente atual."""
    repo_root = Path(__file__).resolve().parents[4]
    env_path = repo_root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)
        name = name.strip()
        if not name or name in os.environ:
            continue

        cleaned = value.strip().strip('"').strip("'")
        os.environ[name] = cleaned


def _env(key: str) -> str | None:
    return os.environ.get(key) or None


def spike_api_football(client: httpx.Client, api_key: str) -> dict:
    """Brasileirão — query compatível com plano free."""
    headers = {"x-apisports-key": api_key}
    fixtures: list[dict] = []
    selected_season: int | None = None
    api_errors: list[dict] = []
    last_response: httpx.Response | None = None

    for season in FREE_PLAN_SEASONS:
        response = client.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={"league": BRAZIL_LEAGUE_ID, "season": season, "status": "FT"},
            timeout=30.0,
        )
        response.raise_for_status()
        last_response = response

        data = response.json()
        errors = data.get("errors") or {}
        if errors:
            api_errors.append({"season": season, "errors": errors})

        fixtures = data.get("response", [])
        if fixtures:
            selected_season = season
            break

    rate_limit_remaining = None
    if last_response is not None:
        rate_limit_remaining = last_response.headers.get("x-ratelimit-requests-remaining")

    return {
        "source": "api_football",
        "league_id": BRAZIL_LEAGUE_ID,
        "season": selected_season,
        "attempted_seasons": list(FREE_PLAN_SEASONS),
        "query_mode": "league+season+status=FT",
        "fixtures_fetched": len(fixtures),
        "rate_limit_remaining": rate_limit_remaining,
        "free_plan_note": "Plano free: temporadas 2022–2024; sem next/last.",
        "api_errors": api_errors,
        "sample": [
            {
                "id": f["fixture"]["id"],
                "home": f["teams"]["home"]["name"],
                "away": f["teams"]["away"]["name"],
                "date": f["fixture"]["date"],
                "score": f"{f['goals']['home']}-{f['goals']['away']}",
            }
            for f in fixtures[:3]
        ],
    }


def spike_the_odds_api(client: httpx.Client, api_key: str) -> dict:
    """Odds de futebol — prioriza Brasileirão."""
    resp = client.get(
        "https://api.the-odds-api.com/v4/sports",
        params={"apiKey": api_key},
        timeout=30.0,
    )
    resp.raise_for_status()
    sports = resp.json()
    soccer_keys = [s["key"] for s in sports if "soccer" in s.get("key", "")]

    odds_result: dict = {
        "source": "the_odds_api",
        "soccer_sports_available": len(soccer_keys),
        "brazil_sport_available": BRAZIL_ODDS_SPORT in soccer_keys,
        "requests_remaining": resp.headers.get("x-requests-remaining"),
    }

    sport_key = BRAZIL_ODDS_SPORT if BRAZIL_ODDS_SPORT in soccer_keys else (soccer_keys[0] if soccer_keys else None)
    if not sport_key:
        return odds_result

    resp2 = client.get(
        f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
        params={
            "apiKey": api_key,
            "regions": "eu,uk",
            "markets": "h2h",
            "oddsFormat": "decimal",
        },
        timeout=30.0,
    )
    resp2.raise_for_status()
    events = resp2.json()
    odds_result["sport_key_used"] = sport_key
    odds_result["events_fetched"] = len(events)
    odds_result["requests_remaining_after"] = resp2.headers.get("x-requests-remaining")
    if events:
        odds_result["sample_event"] = {
            "home": events[0].get("home_team"),
            "away": events[0].get("away_team"),
            "bookmakers": len(events[0].get("bookmakers", [])),
        }
        odds_result["sample_teams"] = [
            {"home": e.get("home_team"), "away": e.get("away_team")} for e in events[:5]
        ]

    return odds_result


def spike_cross_api_match(
    client: httpx.Client,
    api_football_key: str,
    odds_api_key: str,
) -> dict:
    """Tenta cruzar nomes de times entre API-Football e The Odds API."""
    football = spike_api_football(client, api_football_key)
    odds = spike_the_odds_api(client, odds_api_key)

    football_teams: set[str] = set()
    for fx in football.get("sample", []):
        football_teams.add(fx["home"])
        football_teams.add(fx["away"])

    odds_teams: set[str] = set()
    for event in odds.get("sample_teams", []):
        odds_teams.add(event["home"])
        odds_teams.add(event["away"])

    football_list = sorted(football_teams)
    odds_list = sorted(odds_teams)
    matches = []

    for team in football_list:
        match_name, score = best_match(team, odds_list)
        matches.append({
            "api_football": team,
            "the_odds_api": match_name,
            "similarity": round(score, 3),
            "matched": match_name is not None,
        })

    matched_count = sum(1 for m in matches if m["matched"])
    return {
        "source": "cross_api_matching",
        "football_teams_in_sample": len(football_list),
        "odds_teams_in_sample": len(odds_list),
        "matched": matched_count,
        "unmatched": len(football_list) - matched_count,
        "match_rate": round(matched_count / len(football_list), 3) if football_list else 0,
        "pairs": matches,
        "note": "Amostra pequena; Fase 0 exige tabela team_aliases persistida.",
    }


def main() -> None:
    _load_env_file()
    api_football_key = _env("API_FOOTBALL_KEY")
    odds_api_key = _env("THE_ODDS_API_KEY")

    results: dict = {"timestamp": datetime.now(timezone.utc).isoformat(), "checks": []}

    with httpx.Client() as client:
        if api_football_key:
            try:
                results["checks"].append(spike_api_football(client, api_football_key))
            except Exception as exc:  # noqa: BLE001
                results["checks"].append({"source": "api_football", "error": str(exc)})
        else:
            results["checks"].append({
                "source": "api_football",
                "skipped": True,
                "reason": "API_FOOTBALL_KEY not set",
            })

        if odds_api_key:
            try:
                results["checks"].append(spike_the_odds_api(client, odds_api_key))
            except Exception as exc:  # noqa: BLE001
                results["checks"].append({"source": "the_odds_api", "error": str(exc)})
        else:
            results["checks"].append({
                "source": "the_odds_api",
                "skipped": True,
                "reason": "THE_ODDS_API_KEY not set",
            })

        if api_football_key and odds_api_key:
            try:
                results["checks"].append(
                    spike_cross_api_match(client, api_football_key, odds_api_key)
                )
            except Exception as exc:  # noqa: BLE001
                results["checks"].append({"source": "cross_api_matching", "error": str(exc)})

    print(json.dumps(results, indent=2, ensure_ascii=False))

    has_error = any("error" in c for c in results["checks"])
    all_skipped = all(c.get("skipped") for c in results["checks"])
    if has_error:
        sys.exit(1)
    if all_skipped:
        sys.exit(2)


if __name__ == "__main__":
    main()
