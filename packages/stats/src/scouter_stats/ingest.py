"""Fase 0 — pipeline de ingestão: API-Football fixtures + The Odds API odds → Supabase."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

BRAZIL_LEAGUE_ID = 71
BRAZIL_ODDS_SPORT = "soccer_brazil_campeonato"
FREE_PLAN_SEASONS = (2024, 2023, 2022)


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


def _odds_hash(outcomes: dict, market: str, line: float | None) -> str:
    canonical = json.dumps({"market": market, "line": line, "outcomes": outcomes}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# API-Football → matches
# ---------------------------------------------------------------------------

def fetch_fixtures(client: httpx.Client, api_key: str, season: int | None = None) -> list[dict]:
    """Busca fixtures finalizados do Brasileirão."""
    selected_season = season
    if not selected_season:
        for s in FREE_PLAN_SEASONS:
            r = client.get(
                "https://v3.football.api-sports.io/fixtures",
                headers={"x-apisports-key": api_key},
                params={"league": BRAZIL_LEAGUE_ID, "season": s, "status": "FT"},
                timeout=30.0,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("response"):
                selected_season = s
                return data["response"]
        return []

    r = client.get(
        "https://v3.football.api-sports.io/fixtures",
        headers={"x-apisports-key": api_key},
        params={"league": BRAZIL_LEAGUE_ID, "season": selected_season, "status": "FT"},
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json().get("response", [])


def fetch_odds_events(client: httpx.Client, api_key: str) -> list[dict]:
    """Busca odds h2h do Brasileirão via The Odds API."""
    r = client.get(
        f"https://api.the-odds-api.com/v4/sports/{BRAZIL_ODDS_SPORT}/odds",
        params={
            "apiKey": api_key,
            "regions": "eu,uk",
            "markets": "h2h",
            "oddsFormat": "decimal",
        },
        timeout=30.0,
    )
    r.raise_for_status()
    print(f"[odds] requests remaining: {r.headers.get('x-requests-remaining')}")
    return r.json()


# ---------------------------------------------------------------------------
# Supabase insert helpers (via supabase-py)
# ---------------------------------------------------------------------------

def _get_supabase():
    from supabase import create_client

    url = _env("SUPABASE_URL")
    key = _env("SUPABASE_SERVICE_ROLE_KEY") if os.environ.get("SUPABASE_SERVICE_ROLE_KEY") else _env("SUPABASE_ANON_KEY")
    return create_client(url, key)


def ingest_fixtures_to_supabase(fixtures: list[dict]) -> dict:
    """Insere fixtures no Supabase. Retorna contadores."""
    sb = _get_supabase()

    league_row = sb.table("leagues").select("id").eq("slug", "brasileirao-serie-a").single().execute()
    league_id = league_row.data["id"]

    teams_resp = sb.table("teams").select("id, name").eq("league_id", league_id).execute()
    team_map: dict[str, str] = {t["name"].lower(): t["id"] for t in teams_resp.data}

    aliases_resp = sb.table("team_aliases").select("team_id, external_name, source").execute()
    for a in aliases_resp.data:
        team_map[a["external_name"].lower()] = a["team_id"]

    inserted = 0
    skipped = 0
    errors: list[str] = []

    for fx in fixtures:
        home_name = fx["teams"]["home"]["name"]
        away_name = fx["teams"]["away"]["name"]
        home_id = team_map.get(home_name.lower())
        away_id = team_map.get(away_name.lower())

        if not home_id or not away_id:
            errors.append(f"Unmapped team: {home_name} or {away_name}")
            skipped += 1
            continue

        fixture_data = fx["fixture"]
        goals = fx["goals"]

        match_row = {
            "league_id": league_id,
            "home_team_id": home_id,
            "away_team_id": away_id,
            "kickoff_at": fixture_data["date"],
            "status": "finished",
            "home_score": goals.get("home"),
            "away_score": goals.get("away"),
            "venue": (fixture_data.get("venue") or {}).get("name"),
            "round": fx.get("league", {}).get("round"),
        }

        try:
            sb.table("matches").insert(match_row).execute()
            inserted += 1

            # match_mappings
            match_resp = (
                sb.table("matches")
                .select("id")
                .eq("league_id", league_id)
                .eq("home_team_id", home_id)
                .eq("away_team_id", away_id)
                .eq("kickoff_at", fixture_data["date"])
                .limit(1)
                .execute()
            )
            if match_resp.data:
                sb.table("match_mappings").upsert(
                    {
                        "match_id": match_resp.data[0]["id"],
                        "source": "api_football",
                        "external_id": str(fixture_data["id"]),
                    },
                    on_conflict="source,external_id",
                ).execute()
        except Exception as exc:
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                skipped += 1
            else:
                errors.append(str(exc)[:200])
                skipped += 1

    return {"inserted": inserted, "skipped": skipped, "errors": errors[:10]}


def ingest_odds_to_supabase(events: list[dict]) -> dict:
    """Insere odds snapshots no Supabase."""
    sb = _get_supabase()

    league_row = sb.table("leagues").select("id").eq("slug", "brasileirao-serie-a").single().execute()
    league_id = league_row.data["id"]

    teams_resp = sb.table("teams").select("id, name").eq("league_id", league_id).execute()
    team_map: dict[str, str] = {t["name"].lower(): t["id"] for t in teams_resp.data}
    aliases_resp = sb.table("team_aliases").select("team_id, external_name").execute()
    for a in aliases_resp.data:
        team_map[a["external_name"].lower()] = a["team_id"]

    bookmakers_resp = sb.table("bookmakers").select("id, slug").execute()
    bk_map: dict[str, str] = {b["slug"]: b["id"] for b in bookmakers_resp.data}

    inserted = 0
    skipped = 0
    errors: list[str] = []

    for event in events:
        home_name = event.get("home_team", "")
        away_name = event.get("away_team", "")
        home_id = team_map.get(home_name.lower())
        away_id = team_map.get(away_name.lower())

        if not home_id or not away_id:
            skipped += 1
            continue

        match_resp = (
            sb.table("matches")
            .select("id")
            .eq("league_id", league_id)
            .eq("home_team_id", home_id)
            .eq("away_team_id", away_id)
            .order("kickoff_at", desc=True)
            .limit(1)
            .execute()
        )

        if not match_resp.data:
            # Criar match futuro se não existe
            match_row = {
                "league_id": league_id,
                "home_team_id": home_id,
                "away_team_id": away_id,
                "kickoff_at": event.get("commence_time", datetime.now(timezone.utc).isoformat()),
                "status": "scheduled",
            }
            try:
                insert_resp = sb.table("matches").insert(match_row).execute()
                match_id = insert_resp.data[0]["id"]
            except Exception:
                skipped += 1
                continue
        else:
            match_id = match_resp.data[0]["id"]

        for bk in event.get("bookmakers", []):
            bk_slug = bk["key"]
            bk_id = bk_map.get(bk_slug)
            if not bk_id:
                try:
                    new_bk = sb.table("bookmakers").upsert(
                        {"slug": bk_slug, "name": bk.get("title", bk_slug), "is_sharp": bk_slug == "pinnacle"},
                        on_conflict="slug",
                    ).execute()
                    bk_id = new_bk.data[0]["id"]
                    bk_map[bk_slug] = bk_id
                except Exception:
                    continue

            for market_data in bk.get("markets", []):
                market_key = market_data.get("key", "h2h")
                market_type = "h2h" if market_key == "h2h" else market_key

                outcomes_raw = {o["name"].lower(): o["price"] for o in market_data.get("outcomes", [])}
                outcomes_mapped = {}
                for k, v in outcomes_raw.items():
                    if k in ("home", "draw", "away"):
                        outcomes_mapped[k] = v
                    elif k == home_name.lower() or "home" in k:
                        outcomes_mapped["home"] = v
                    elif k == away_name.lower() or "away" in k:
                        outcomes_mapped["away"] = v
                    elif k == "draw" or k == "tie":
                        outcomes_mapped["draw"] = v
                    else:
                        outcomes_mapped[k] = v

                oh = _odds_hash(outcomes_mapped, market_type, None)

                row = {
                    "match_id": match_id,
                    "bookmaker_id": bk_id,
                    "market": market_type,
                    "outcomes": outcomes_mapped,
                    "odds_hash": oh,
                    "source": "the_odds_api",
                }

                try:
                    sb.table("odds_snapshots").insert(row).execute()
                    inserted += 1
                except Exception as exc:
                    if "duplicate" in str(exc).lower():
                        skipped += 1
                    else:
                        errors.append(str(exc)[:150])

    return {"inserted": inserted, "skipped": skipped, "errors": errors[:10]}


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    _load_env()

    api_football_key = _env("API_FOOTBALL_KEY")
    odds_api_key = _env("THE_ODDS_API_KEY")

    print(f"[ingest] started at {datetime.now(timezone.utc).isoformat()}")

    with httpx.Client() as client:
        # 1) Fixtures
        print("[ingest] fetching fixtures from API-Football...")
        fixtures = fetch_fixtures(client, api_football_key)
        print(f"[ingest] fetched {len(fixtures)} fixtures")

        if fixtures:
            result = ingest_fixtures_to_supabase(fixtures)
            print(f"[ingest] matches: {result}")

        # 2) Odds
        print("[ingest] fetching odds from The Odds API...")
        events = fetch_odds_events(client, odds_api_key)
        print(f"[ingest] fetched {len(events)} events with odds")

        if events:
            result = ingest_odds_to_supabase(events)
            print(f"[ingest] odds_snapshots: {result}")

    print("[ingest] done")


if __name__ == "__main__":
    main()
