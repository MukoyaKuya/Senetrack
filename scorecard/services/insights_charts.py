"""
Pure functions to build chart data for the Data Insights dashboard.

Consumes precomputed aggregates from the insights view and returns
the charts dict expected by the frontend (JSON-serialized in template).
"""
from __future__ import annotations

from typing import Any, Dict, List


def build_insights_charts(aggregates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the charts dict for the insights page from precomputed aggregates.

    aggregates must contain:
      - rows: list of senator row dicts
      - bins: list of 10 ints (score distribution)
      - frontier_chart: list of {frontier, avg_score}
      - top_sponsored: list of top 10 rows by sponsored_bills
      - committee_leadership_impact: {leaders_avg, members_avg, leaders_count, members_count}
      - county_performance: list of {county, avg_score, avg_attendance, avg_bills}
      - grade_distribution: list of {grade, count}
      - committee_role_stats: list of {role, count, avg_score}
      - party_performance: list of {party, count, avg_score}
      - frontier_by_metric: list of {frontier, avg_score, avg_attendance, avg_bills, avg_speeches, avg_words}
      - nominated: list of rows (nominated senators)
      - elected: list of rows (elected senators)
      - nom_avg_score, elec_avg_score, nom_avg_att, elec_avg_att: floats
      - grade_tier_stats: list of {grade, avg_words, avg_speeches, avg_motions, avg_structural, avg_debate}
      - sorted_rows: rows sorted by overall_score desc (used for structural_vs_debate top 15)
    """
    rows = aggregates.get("rows") or []
    bins = aggregates.get("bins") or [0] * 10
    frontier_chart = aggregates.get("frontier_chart") or []
    top_sponsored = aggregates.get("top_sponsored") or []
    committee_leadership_impact = aggregates.get("committee_leadership_impact") or {}
    county_performance = aggregates.get("county_performance") or []
    grade_distribution = aggregates.get("grade_distribution") or []
    committee_role_stats = aggregates.get("committee_role_stats") or []
    party_performance = aggregates.get("party_performance") or []
    frontier_by_metric = aggregates.get("frontier_by_metric") or []
    nominated = aggregates.get("nominated") or []
    elected = aggregates.get("elected") or []
    nom_avg_score = aggregates.get("nom_avg_score") or 0.0
    elec_avg_score = aggregates.get("elec_avg_score") or 0.0
    nom_avg_att = aggregates.get("nom_avg_att") or 0.0
    elec_avg_att = aggregates.get("elec_avg_att") or 0.0
    grade_tier_stats = aggregates.get("grade_tier_stats") or []
    sorted_rows = aggregates.get("sorted_rows") or sorted(rows, key=lambda r: r.get("overall_score", 0), reverse=True)

    def _trunc(s: str, n: int) -> str:
        return (s[:n] + "…") if len(s) > n else s

    charts: Dict[str, Any] = {
        "score_distribution": {
            "labels": ["0–9", "10–19", "20–29", "30–39", "40–49", "50–59", "60–69", "70–79", "80–89", "90–99"],
            "counts": bins,
        },
        "frontier_scores": {
            "labels": [fs["frontier"].replace("_", " ").title() for fs in frontier_chart],
            "scores": [fs["avg_score"] for fs in frontier_chart],
        },
        "attendance_vs_score": {
            "labels": [r["name"] for r in rows],
            "attendance": [round(r["attendance_rate"], 1) for r in rows],
            "scores": [r["overall_score"] for r in rows],
        },
        "bills_sponsored_vs_passed": {
            "labels": [r["name"] for r in top_sponsored],
            "sponsored": [r["sponsored_bills"] for r in top_sponsored],
            "passed": [r["passed_bills"] for r in top_sponsored],
        },
        "speeches_vs_score": {
            "speeches": [r["speeches"] for r in rows],
            "scores": [r["overall_score"] for r in rows],
        },
        "words_vs_score": {
            "words": [r["words_spoken"] for r in rows],
            "scores": [r["overall_score"] for r in rows],
        },
        "structural_vs_debate": {
            "labels": [_trunc(r["name"], 15) for r in sorted_rows[:15]],
            "structural": [r["structural_score"] for r in sorted_rows[:15]],
            "debate": [r["debate_score"] for r in sorted_rows[:15]],
        },
        "amendments_vs_passed": {
            "amendments": [r["amendments"] for r in rows],
            "passed": [r["passed_bills"] for r in rows],
        },
        "grade_distribution": {
            "labels": [g["grade"] for g in grade_distribution],
            "counts": [g["count"] for g in grade_distribution],
        },
        "committee_role_chart": {
            "labels": [c["role"] for c in committee_role_stats],
            "counts": [c["count"] for c in committee_role_stats],
            "avg_scores": [c["avg_score"] for c in committee_role_stats],
        },
        "party_performance": {
            "labels": [_trunc(p["party"], 20) for p in party_performance],
            "counts": [p["count"] for p in party_performance],
            "avg_scores": [p["avg_score"] for p in party_performance],
        },
        "frontier_by_metric": {
            "labels": [f["frontier"].replace("_", " ").title() for f in frontier_by_metric],
            "avg_scores": [f["avg_score"] for f in frontier_by_metric],
            "avg_attendance": [f["avg_attendance"] for f in frontier_by_metric],
            "avg_bills": [f["avg_bills"] for f in frontier_by_metric],
            "avg_speeches": [f["avg_speeches"] for f in frontier_by_metric],
            "avg_words": [f["avg_words"] for f in frontier_by_metric],
        },
        "nominated_vs_elected": {
            "labels": ["Nominated", "Elected"],
            "avg_scores": [nom_avg_score, elec_avg_score],
            "avg_attendance": [nom_avg_att, elec_avg_att],
            "counts": [len(nominated), len(elected)],
        },
        "committee_leadership": {
            "labels": ["Leaders (Chair/Vice etc.)", "Members"],
            "avg_scores": [
                committee_leadership_impact.get("leaders_avg", 0),
                committee_leadership_impact.get("members_avg", 0),
            ],
            "counts": [
                committee_leadership_impact.get("leaders_count", 0),
                committee_leadership_impact.get("members_count", 0),
            ],
        },
        "county_performance": {
            "labels": [_trunc(c["county"], 25) for c in county_performance],
            "avg_scores": [c["avg_score"] for c in county_performance],
            "avg_attendance": [c["avg_attendance"] for c in county_performance],
            "avg_bills": [c["avg_bills"] for c in county_performance],
        },
        "grade_tier_stats": {
            "labels": [g["grade"] for g in grade_tier_stats],
            "avg_words": [g["avg_words"] for g in grade_tier_stats],
            "avg_speeches": [g["avg_speeches"] for g in grade_tier_stats],
            "avg_motions": [g["avg_motions"] for g in grade_tier_stats],
            "avg_structural": [g["avg_structural"] for g in grade_tier_stats],
            "avg_debate": [g["avg_debate"] for g in grade_tier_stats],
        },
    }
    return charts
