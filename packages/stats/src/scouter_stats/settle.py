"""Settle published predictions against finished match scores.

Writes prediction_results and refreshes accuracy_snapshots.
Requires SUPABASE_SERVICE_ROLE_KEY (anon write policies revoked).
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import date
from typing import Any

from scouter_stats.supabase_client import get_supabase


def _actual_h2h(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home"
    if home_score < away_score:
        return "away"
    return "draw"


def settle_predictions(sb: Any) -> dict[str, int]:
    preds = (
        sb.table("predictions")
        .select("id,selection,market,risk_label,match_id,matches(status,home_score,away_score)")
        .execute()
        .data
        or []
    )
    existing = {
        row["prediction_id"]
        for row in (sb.table("prediction_results").select("prediction_id").execute().data or [])
    }

    rows: list[dict[str, Any]] = []
    for p in preds:
        if p["id"] in existing:
            continue
        match = p.get("matches") or {}
        if match.get("status") != "finished":
            continue
        home = match.get("home_score")
        away = match.get("away_score")
        if home is None or away is None:
            continue
        if p["market"] != "h2h":
            continue
        actual = _actual_h2h(int(home), int(away))
        rows.append(
            {
                "prediction_id": p["id"],
                "actual_outcome": actual,
                "was_correct": p["selection"] == actual,
                "settlement_reason": "finished",
            }
        )

    if rows:
        sb.table("prediction_results").upsert(rows, on_conflict="prediction_id").execute()

    return {
        "settled": len(rows),
        "correct": sum(1 for r in rows if r["was_correct"]),
        "incorrect": sum(1 for r in rows if not r["was_correct"]),
    }


def refresh_accuracy(sb: Any) -> int:
    joined = (
        sb.table("prediction_results")
        .select("was_correct,settled_at,predictions(market,risk_label)")
        .execute()
        .data
        or []
    )
    if not joined:
        return 0

    buckets: dict[tuple[str, str | None], dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "correct": 0, "starts": [], "ends": []}
    )
    for row in joined:
        pred = row.get("predictions") or {}
        market = pred.get("market")
        if not market:
            continue
        risk = pred.get("risk_label")
        key = (market, risk)
        buckets[key]["total"] += 1
        if row.get("was_correct"):
            buckets[key]["correct"] += 1
        settled = (row.get("settled_at") or "")[:10]
        if settled:
            buckets[key]["starts"].append(settled)
            buckets[key]["ends"].append(settled)

    upserts = []
    today = date.today().isoformat()
    for (market, risk), agg in buckets.items():
        starts = agg["starts"] or [today]
        ends = agg["ends"] or [today]
        total = agg["total"]
        correct = agg["correct"]
        upserts.append(
            {
                "period_start": min(starts),
                "period_end": max(ends),
                "market": market,
                "risk_label": risk,
                "total_predictions": total,
                "correct_predictions": correct,
                "accuracy_pct": round(100.0 * correct / total, 2) if total else 0.0,
                "methodology_version": "v1",
            }
        )

    if upserts:
        sb.table("accuracy_snapshots").upsert(
            upserts,
            on_conflict="period_start,period_end,market,risk_label,methodology_version",
        ).execute()
    return len(upserts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Settle prediction results")
    parser.add_argument("--skip-accuracy", action="store_true")
    args = parser.parse_args(argv)

    sb = get_supabase(require_service_role=True)
    stats = settle_predictions(sb)
    print(f"[settle] settled={stats['settled']} correct={stats['correct']} incorrect={stats['incorrect']}")
    if not args.skip_accuracy:
        n = refresh_accuracy(sb)
        print(f"[settle] accuracy_snapshots upserted={n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
