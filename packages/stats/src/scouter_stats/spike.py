"""Spike Fase 0 — valida conectividade e limites das APIs externas."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import httpx


def _env(key: str) -> str | None:
    return os.environ.get(key) or None


def spike_api_football(client: httpx.Client, api_key: str) -> dict:
    """Brasileirão: liga 71 (API-Football v3)."""
    league_id = 71
    season = datetime.now(timezone.utc).year

    resp = client.get(
        "https://v3.football.api-sports.io/fixtures",
        headers={"x-apisports-key": api_key},
        params={"league": league_id, "season": season, "next": 5},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()

    fixtures = data.get("response", [])
    return {
        "source": "api_football",
        "league_id": league_id,
        "season": season,
        "fixtures_fetched": len(fixtures),
        "rate_limit_remaining": resp.headers.get("x-ratelimit-requests-remaining"),
        "sample": [
            {
                "id": f["fixture"]["id"],
                "home": f["teams"]["home"]["name"],
                "away": f["teams"]["away"]["name"],
                "date": f["fixture"]["date"],
            }
            for f in fixtures[:3]
        ],
    }


def spike_the_odds_api(client: httpx.Client, api_key: str) -> dict:
    """Odds de futebol — região BR quando disponível."""
    resp = client.get(
        "https://api.the-odds-api.com/v4/sports",
        params={"apiKey": api_key},
        timeout=30.0,
    )
    resp.raise_for_status()
    sports = resp.json()
    soccer_keys = [s["key"] for s in sports if "soccer" in s.get("key", "")][:5]

    odds_result: dict = {
        "source": "the_odds_api",
        "soccer_sports_available": len([s for s in sports if "soccer" in s.get("key", "")]),
        "sample_sport_keys": soccer_keys,
        "requests_remaining": resp.headers.get("x-requests-remaining"),
    }

    if soccer_keys:
        resp2 = client.get(
            f"https://api.the-odds-api.com/v4/sports/{soccer_keys[0]}/odds",
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
        odds_result["events_fetched"] = len(events)
        odds_result["requests_remaining_after"] = resp2.headers.get("x-requests-remaining")
        if events:
            odds_result["sample_event"] = {
                "home": events[0].get("home_team"),
                "away": events[0].get("away_team"),
                "bookmakers": len(events[0].get("bookmakers", [])),
            }

    return odds_result


def main() -> None:
    api_football_key = _env("API_FOOTBALL_KEY")
    odds_api_key = _env("THE_ODDS_API_KEY")

    results: dict = {"timestamp": datetime.now(timezone.utc).isoformat(), "checks": []}

    with httpx.Client() as client:
        if api_football_key:
            try:
                results["checks"].append(spike_api_football(client, api_football_key))
            except Exception as exc:  # noqa: BLE001 — spike reporta falha
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

    print(json.dumps(results, indent=2, ensure_ascii=False))

    has_error = any("error" in c for c in results["checks"])
    all_skipped = all(c.get("skipped") for c in results["checks"])
    if has_error:
        sys.exit(1)
    if all_skipped:
        sys.exit(2)  # keys missing — esperado em dev sem .env


if __name__ == "__main__":
    main()
