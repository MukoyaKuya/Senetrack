from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _percentile_rank_desc(values: List[float], value: float) -> float:
    """
    Percentile rank where higher is better (descending).
    Returns 0..1 (e.g. 0.8 means top 20%).
    """
    vals = [v for v in values if v is not None]
    if not vals:
        return 0.0
    vals.sort()
    # percentile in ascending order, then flip
    # (count of <= value) / n  => higher value => higher percentile
    n = len(vals)
    leq = 0
    for v in vals:
        if v <= value:
            leq += 1
        else:
            break
    asc = leq / n
    return asc


def build_profile_insights(
    senator_row: Dict[str, Any],
    all_rows: List[Dict[str, Any]],
    *,
    top_pct: float = 0.30,
    bottom_pct: float = 0.30,
    max_items: int = 5,
) -> Dict[str, List[str]]:
    """
    Generate Key Strengths / Growth Areas for a senator profile.

    Uses cohort-relative percentiles (top/bottom bands) plus a few guardrails
    so the messages stay intuitive and consistent.
    """
    sid = senator_row.get("senator_id")
    cohort = [r for r in all_rows if r.get("senator_id") != sid]

    def col(name: str) -> List[float]:
        out: List[float] = []
        for r in cohort:
            try:
                out.append(float(r.get(name) or 0))
            except Exception:
                out.append(0.0)
        return out

    def val(name: str) -> float:
        try:
            return float(senator_row.get(name) or 0)
        except Exception:
            return 0.0

    attendance = val("attendance_rate")
    vote_rate = val("vote_rate")
    sponsored = val("sponsored_bills")
    passed = val("passed_bills")
    words = val("words_spoken")
    speeches = val("speeches")
    motions = val("motions_sponsored")
    statements = val("statements_2025")

    p_att = _percentile_rank_desc(col("attendance_rate"), attendance)
    p_vote = _percentile_rank_desc(col("vote_rate"), vote_rate)
    p_sponsored = _percentile_rank_desc(col("sponsored_bills"), sponsored)
    p_passed = _percentile_rank_desc(col("passed_bills"), passed)
    p_words = _percentile_rank_desc(col("words_spoken"), words)
    p_speeches = _percentile_rank_desc(col("speeches"), speeches)
    p_motions = _percentile_rank_desc(col("motions_sponsored"), motions)
    p_statements = _percentile_rank_desc(col("statements_2025"), statements)

    strengths: List[str] = []
    growth: List[str] = []

    # Strengths (top band)
    if p_att >= 1 - top_pct and attendance > 0:
        strengths.append("Elite Attendance: Consistently present across sessions.")
    elif attendance >= 80:
        strengths.append("High Floor Attendance: Maintains a strong presence in the Senate.")

    if p_vote >= 1 - top_pct and vote_rate > 0:
        strengths.append("Exceptional Voting Record: Participating in nearly all key legislative decisions.")

    if (p_sponsored >= 1 - top_pct and sponsored > 0) or sponsored >= 3:
        strengths.append("Active Legislator: Demonstrates strong bill sponsorship activity.")

    if (p_passed >= 1 - top_pct and passed > 0) or passed >= 2:
        strengths.append("Legislative Impact: Strong record of bills progressing and/or passing.")

    if p_words >= 1 - top_pct and words > 0:
        strengths.append("Prolific Speaker: High contribution to Hansard debates by word count.")

    if p_speeches >= 1 - top_pct and speeches > 0:
        strengths.append("Active Floor Contributor: Frequently engages in plenary debate.")

    if (p_motions >= 1 - top_pct and motions > 0) or (p_statements >= 1 - top_pct and statements > 0):
        strengths.append("Strong Oversight & Representation: Uses motions/statements to raise public issues.")

    # Growth areas (bottom band + guardrails)
    if p_att <= bottom_pct and attendance > 0:
        growth.append("Improve Attendance: Session participation is below the national benchmark.")
    elif attendance == 0:
        growth.append("Attendance Data: Missing/insufficient attendance data recorded.")

    if p_vote <= bottom_pct and vote_rate > 0:
        growth.append("Voting Diligence: Increase participation during division votes.")

    if sponsored == 0:
        growth.append("Legislative Initiative: No bills sponsored during this period.")
    elif p_sponsored <= bottom_pct and sponsored > 0:
        growth.append("Legislative Initiative: Increase bill sponsorship to strengthen legislative footprint.")

    if (motions + statements) == 0:
        growth.append("Oversight Engagement: Low frequency of statements/motions sponsored.")
    elif (p_motions <= bottom_pct and motions > 0) and (p_statements <= bottom_pct and statements > 0):
        growth.append("Oversight Engagement: Increase statements/motions to deepen constituent representation.")

    if p_words <= bottom_pct and p_speeches <= bottom_pct and (words > 0 or speeches > 0):
        growth.append("Floor Participation: Limited verbal contribution to Senate proceedings.")

    # De-dup & cap
    def uniq(items: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in items:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    strengths = uniq(strengths)[:max_items]
    growth = uniq(growth)[:max_items]

    # Always provide at least one growth hint, but allow strengths to be empty
    # when the senator sits around the cohort median on all tracked metrics.
    if not growth:
        growth = ["Maintain current standards across all measured KPIs."]

    return {"strengths": strengths, "improvements": growth}

