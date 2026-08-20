"""Ingestão de contexto qualitativo — lesões + escalações (API-Football)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

BRAZIL_LEAGUE_ID = 71


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


def _importance_from_reason(reason: str | None) -> str:
    text = (reason or "").lower()
    if any(k in text for k in ("acl", "cruciate", "fracture", "surgery", "rupture")):
        return "high"
    if any(k in text for k in ("injury", "muscle", "hamstring", "knee", "ankle")):
        return "medium"
    if any(k in text for k in ("suspension", "red card", "yellow")):
        return "medium"
    return "low"


def _absence_status(player_type: str | None, reason: str | None) -> str:
    combined = f"{player_type or ''} {reason or ''}".lower()
    if "doubt" in combined:
        return "doubtful"
    if "suspend" in combined:
        return "suspended"
    return "confirmed_out"


def fetch_injuries(client: httpx.Client, api_key: str, season: int) -> list[dict]:
    response = client.get(
        "https://v3.football.api-sports.io/injuries",
        headers={"x-apisports-key": api_key},
        params={"league": BRAZIL_LEAGUE_ID, "season": season},
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("errors"):
        raise RuntimeError(f"API-Football injuries errors: {data['errors']}")
    return data.get("response", [])


def fetch_lineups(client: httpx.Client, api_key: str, fixture_id: int) -> list[dict]:
    response = client.get(
        "https://v3.football.api-sports.io/fixtures/lineups",
        headers={"x-apisports-key": api_key},
        params={"fixture": fixture_id},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("errors"):
        return []
    return data.get("response", [])


def ingest_injuries(sb, injuries: list[dict]) -> dict:
    mappings = (
        sb.table("match_mappings")
        .select("match_id, external_id")
        .eq("source", "api_football")
        .execute()
        .data
    )
    fixture_to_match = {m["external_id"]: m["match_id"] for m in mappings}

    teams = sb.table("teams").select("id, name").execute().data
    team_map = {t["name"].lower(): t["id"] for t in teams}
    aliases = sb.table("team_aliases").select("team_id, external_name").execute().data
    for a in aliases:
        team_map[a["external_name"].lower()] = a["team_id"]

    skipped = 0
    by_match: dict[str, int] = defaultdict(int)
    batch: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()

    for row in injuries:
        fixture_id = str((row.get("fixture") or {}).get("id") or "")
        match_id = fixture_to_match.get(fixture_id)
        if not match_id:
            skipped += 1
            continue

        team_name = (row.get("team") or {}).get("name") or ""
        team_id = team_map.get(team_name.lower())
        if not team_id:
            skipped += 1
            continue

        player = row.get("player") or {}
        player_name = player.get("name") or "Unknown"
        status = _absence_status(player.get("type"), player.get("reason"))
        importance = _importance_from_reason(player.get("reason"))
        key = (match_id, team_id, player_name, status)
        if key in seen:
            skipped += 1
            continue
        seen.add(key)

        batch.append({
            "match_id": match_id,
            "team_id": team_id,
            "player_name": player_name,
            "player_external_id": str(player.get("id")) if player.get("id") else None,
            "absence_status": status,
            "role": player.get("type"),
            "importance": importance,
            "source": "api_football",
        })
        by_match[match_id] += 1

    inserted = 0
    chunk_size = 100
    for i in range(0, len(batch), chunk_size):
        chunk = batch[i : i + chunk_size]
        try:
            sb.table("match_absences").upsert(
                chunk,
                on_conflict="match_id,team_id,player_name,absence_status",
            ).execute()
            inserted += len(chunk)
            print(f"[context] absences upserted {inserted}/{len(batch)}")
        except Exception as exc:
            # fallback unitário no chunk com falha
            for row in chunk:
                try:
                    sb.table("match_absences").upsert(
                        row,
                        on_conflict="match_id,team_id,player_name,absence_status",
                    ).execute()
                    inserted += 1
                except Exception:
                    skipped += 1
            print(f"[context] chunk fallback after error: {str(exc)[:120]}")

    return {
        "inserted": inserted,
        "skipped": skipped,
        "matches_with_absences": len(by_match),
    }


def upsert_match_context(
    sb,
    *,
    match_id: str,
    lineup_status: str,
    absences: list[dict],
    lineup_payload: list[dict] | None = None,
) -> None:
    missing = []
    if lineup_status == "UNKNOWN":
        missing.append("lineup")

    # absences_known = True because we queried the injuries feed for this match
    pack = {
        "lineup_status": lineup_status,
        "absences": [
            {
                "player": a.get("player_name"),
                "status": a.get("absence_status"),
                "importance": a.get("importance"),
                "team_id": a.get("team_id"),
            }
            for a in absences
        ],
        "lineups": lineup_payload or [],
        "missing": missing,
    }
    high = sum(1 for a in absences if a.get("importance") == "high")
    completeness = 0.30 + 0.25  # prior+odds assumed when judging
    completeness += 0.15  # sample not thin unknown here — leave to judge
    if lineup_status == "CONFIRMED":
        completeness += 0.20
    elif lineup_status == "PROBABLE":
        completeness += 0.10
    completeness += 0.10  # absences known
    completeness = round(min(1.0, completeness), 3)

    pack_hash = hashlib.sha256(json.dumps(pack, sort_keys=True).encode()).hexdigest()[:16]
    row = {
        "match_id": match_id,
        "lineup_status": lineup_status,
        "lineup_confirmed_at": datetime.now(timezone.utc).isoformat() if lineup_status == "CONFIRMED" else None,
        "missing_fields": missing,
        "information_completeness": completeness,
        "pack_hash": pack_hash,
        "pack": pack,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    existing = (
        sb.table("match_context")
        .select("id")
        .eq("match_id", match_id)
        .eq("pack_hash", pack_hash)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        sb.table("match_context").update(row).eq("id", existing[0]["id"]).execute()
    else:
        # keep latest only: update any row for match or insert
        any_row = (
            sb.table("match_context")
            .select("id")
            .eq("match_id", match_id)
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if any_row:
            sb.table("match_context").update(row).eq("id", any_row[0]["id"]).execute()
        else:
            sb.table("match_context").insert(row).execute()


def build_contexts_for_judgable_matches(
    client: httpx.Client,
    api_key: str,
    sb,
    *,
    limit_lineups: int = 20,
) -> dict:
    """Monta match_context para jogos que têm prior+odds; busca lineups quando possível."""
    # matches that appear in odds
    odds = sb.table("odds_snapshots").select("match_id").eq("market", "h2h").execute().data
    match_ids = list({o["match_id"] for o in odds})
    if not match_ids:
        return {"contexts": 0, "lineups_fetched": 0}

    mappings = (
        sb.table("match_mappings")
        .select("match_id, external_id")
        .eq("source", "api_football")
        .in_("match_id", match_ids)
        .execute()
        .data
    )
    match_to_fixture = {m["match_id"]: m["external_id"] for m in mappings}

    absences_all = (
        sb.table("match_absences")
        .select("*")
        .in_("match_id", match_ids)
        .execute()
        .data
    )
    abs_by_match: dict[str, list] = defaultdict(list)
    for a in absences_all:
        abs_by_match[a["match_id"]].append(a)

    contexts = 0
    lineups_fetched = 0
    for mid in match_ids[: max(limit_lineups * 3, limit_lineups)]:
        lineup_status = "UNKNOWN"
        lineup_payload = None
        fixture_id = match_to_fixture.get(mid)
        if fixture_id and lineups_fetched < limit_lineups:
            try:
                lineups = fetch_lineups(client, api_key, int(fixture_id))
                if lineups:
                    lineup_status = "CONFIRMED"
                    lineup_payload = [
                        {
                            "team": (lu.get("team") or {}).get("name"),
                            "formation": lu.get("formation"),
                            "startXI": [
                                (p.get("player") or {}).get("name")
                                for p in lu.get("startXI", [])
                            ],
                        }
                        for lu in lineups
                    ]
                    lineups_fetched += 1
            except Exception:
                pass

        upsert_match_context(
            sb,
            match_id=mid,
            lineup_status=lineup_status,
            absences=abs_by_match.get(mid, []),
            lineup_payload=lineup_payload,
        )
        contexts += 1

    return {"contexts": contexts, "lineups_fetched": lineups_fetched}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest injuries + lineups into match context")
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--lineups-limit", type=int, default=15)
    args = parser.parse_args()

    _load_env()
    api_key = _env("API_FOOTBALL_KEY")
    sb = _get_supabase()

    with httpx.Client() as client:
        print(f"[context] fetching injuries season={args.season}")
        injuries = fetch_injuries(client, api_key, args.season)
        print(f"[context] injuries rows={len(injuries)}")
        injury_result = ingest_injuries(sb, injuries)
        print(f"[context] absences={injury_result}")

        print("[context] building match_context + lineups")
        ctx_result = build_contexts_for_judgable_matches(
            client, api_key, sb, limit_lineups=args.lineups_limit
        )
        print(f"[context] contexts={ctx_result}")

    print(json.dumps({"ok": True, "injuries": injury_result, "contexts": ctx_result}, indent=2))


if __name__ == "__main__":
    main()
