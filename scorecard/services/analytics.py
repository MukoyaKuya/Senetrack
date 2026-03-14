from __future__ import annotations

from typing import Any, Dict, List

from django.core.cache import cache

from scorecard.engine import get_engine_result
from scorecard.models import Senator
from scorecard.services.senators import get_frontier

SENATOR_ROWS_CACHE_KEY = "scorecard:senator_rows"
SENATOR_ROWS_CACHE_TIMEOUT = 300  # 5 minutes


def get_senator_rows() -> List[Dict[str, Any]]:
    """
    Return senator performance rows, from cache when available (5 min TTL).
    Reduces DB and CPU load under concurrency for insights and frontier views.
    """
    rows = cache.get(SENATOR_ROWS_CACHE_KEY)
    if rows is not None:
        return rows
    rows = build_senator_rows()
    cache.set(SENATOR_ROWS_CACHE_KEY, rows, SENATOR_ROWS_CACHE_TIMEOUT)
    return rows


def build_senator_rows() -> List[Dict[str, Any]]:
    """
    Build senator performance rows for analytics.

    Shared by data_insights and frontier_insights so that aggregation logic
    lives in one place instead of directly in the views module.
    """
    senators_qs = (
        Senator.objects.filter(perf__isnull=False, is_deceased=False)
        .select_related("perf", "county_fk")
    )
    rows: List[Dict[str, Any]] = []
    for s in senators_qs:
        res = get_engine_result(getattr(s, "perf", None))
        if not res:
            continue
        frontier = get_frontier(s)
        attended_votes = getattr(s.perf, "attended_votes", 0) or 0
        total_votes_val = max(getattr(s.perf, "total_votes", 20) or 20, 1)
        vote_rate = round((attended_votes / total_votes_val) * 100, 1) if total_votes_val else 0.0
        votes_missed = total_votes_val - attended_votes

        county_fk = getattr(s, "county_fk", None)
        county_name = getattr(county_fk, "name", "")
        county_slug = getattr(county_fk, "slug", "")
        is_nominated = bool((s.nomination or "").strip()) or "nominated" in (county_name or "").lower()
        county_rep = round(float(getattr(s.perf, "county_representation_score", 0) or 0), 1)
        committee_role = (getattr(s.perf, "committee_role", "Member") or "Member").strip() or "Member"
        trend_data = getattr(s.perf, "trend_data", None) or []

        image_url = s.image.url if s.image else (s.image_url or "")

        # Use sessions-based attendance when Hansard data exists (sessions_attended)
        sessions_att = getattr(s.perf, "sessions_attended", 0) or 0
        att_rate = round(getattr(s.perf, "attendance_rate", 0.0) or 0.0, 1)
        if sessions_att > 0:
            att_rate = round((sessions_att / 102.0) * 100, 1)

        rows.append(
            {
                "name": s.name,
                "senator_id": s.senator_id,
                "image_url": image_url,
                "county": county_name,
                "county_slug": county_slug,
                "nomination": (getattr(s, "nomination", None) or "").strip(),
                "party": (s.party or "").strip() or "Unknown",
                "frontier": frontier,
                "overall_score": res.get("overall_score", 0),
                "grade": res.get("grade", "—"),
                "structural_score": round(getattr(s.perf, "structural_score", 0) or 0, 1),
                "debate_score": round(getattr(s.perf, "debate_score", 0) or 0, 1),
                "attendance_rate": att_rate,
                "speeches": getattr(s.perf, "speeches", 0) or 0,
                "words_spoken": getattr(s.perf, "words_spoken", 0) or 0,
                "motions_sponsored": getattr(s.perf, "motions_sponsored", 0) or 0,
                "sessions_attended": sessions_att,
                "sponsored_bills": getattr(s.perf, "sponsored_bills", 0) or 0,
                "passed_bills": getattr(s.perf, "passed_bills", 0) or 0,
                "amendments": getattr(s.perf, "amendments", 0) or 0,
                "committee_attendance": round(
                    getattr(s.perf, "committee_attendance", 0.0) or 0.0, 1
                ),
                "vote_rate": vote_rate,
                "votes_missed": votes_missed,
                "oversight_actions": getattr(s.perf, "oversight_actions", 0) or 0,
                "county_representation": county_rep,
                "committee_role": committee_role,
                "is_nominated": is_nominated,
                "trend_data": trend_data if isinstance(trend_data, list) else [],
                "statements_2025": getattr(s.perf, "statements_2025", 0) or 0,
            }
        )
    return rows


def normalize_frontier(value: str) -> str:
    """Normalize frontier for consistent filter matching (case-insensitive, spaces to underscores)."""
    return (value or "").strip().replace(" ", "_").lower()

