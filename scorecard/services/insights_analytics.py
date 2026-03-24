"""
Analytics computation for the data insights dashboard.

Separates pure data crunching from the view layer so each piece can be
tested and iterated on independently.
"""


GRADE_ORDER = {
    "A": 0, "A-": 1, "B+": 2, "B": 3, "B-": 4,
    "C+": 5, "C": 6, "C-": 7, "D+": 8, "D": 9,
    "D-": 10, "E": 11, "NEW": 12, "—": 13,
}


def _percentile_rank(val, sorted_arr):
    below = sum(1 for x in sorted_arr if x < val)
    return round((below / len(sorted_arr)) * 100, 0) if sorted_arr else 0


def enrich_rows_with_computed_metrics(rows):
    """Mutate each row in-place with derived per-senator metrics."""
    for r in rows:
        sessions = r.get("sessions_attended") or 0
        speeches = r.get("speeches") or 0
        bills = r.get("sponsored_bills") or 0
        words = r.get("words_spoken") or 0
        motions = r.get("motions_sponsored") or 0
        s_sc = r.get("structural_score") or 0
        d_sc = r.get("debate_score") or 0

        r["speeches_per_session"] = round(speeches / sessions, 1) if sessions else 0
        r["bills_per_session"] = round(bills / sessions, 2) if sessions else 0
        r["bills_per_speech"] = round(bills / speeches, 2) if speeches else 0
        r["motions_per_speech"] = round(motions / speeches, 2) if speeches else 0
        r["words_per_speech"] = round(words / speeches, 1) if speeches else 0
        r["structural_debate_ratio"] = round(s_sc / d_sc, 2) if d_sc else (s_sc if s_sc else 0)
        r["floor_leader_index"] = round(min(100, (words / 1500 + speeches / 35 + motions * 2)), 1)
        r["legislative_workhorse_index"] = round(min(100, (bills * 5 + r.get("vote_rate", 0) * 0.3 + sessions / 1.2)), 1)
        r["balanced_contributor"] = round(100 - abs(s_sc - d_sc), 1) if (s_sc or d_sc) else 0
    return rows


def build_leaderboards(rows):
    """Return all leaderboard lists derived from senator rows."""
    n = len(rows)
    verbosity_rows = [r for r in rows if r["speeches"] >= 10]

    top_attendance = sorted(rows, key=lambda r: r["attendance_rate"], reverse=True)[:10]
    top_sponsored = sorted(rows, key=lambda r: r["sponsored_bills"], reverse=True)[:10]
    top_passed = sorted(rows, key=lambda r: r["passed_bills"], reverse=True)[:10]
    top_speeches = sorted(rows, key=lambda r: r["speeches"], reverse=True)[:10]
    top_words = sorted(rows, key=lambda r: r["words_spoken"], reverse=True)[:10]
    top_motions = sorted(rows, key=lambda r: r["motions_sponsored"], reverse=True)[:10]
    top_sessions = sorted(rows, key=lambda r: r["sessions_attended"], reverse=True)[:10]
    top_amendments = sorted(rows, key=lambda r: r["amendments"], reverse=True)[:10]
    top_committee = sorted(rows, key=lambda r: r["committee_attendance"], reverse=True)[:10]
    top_vote_rate = sorted(rows, key=lambda r: r["vote_rate"], reverse=True)[:10]
    top_oversight = sorted(rows, key=lambda r: r["oversight_actions"], reverse=True)[:10]
    top_county_rep = sorted(rows, key=lambda r: r["county_representation"], reverse=True)[:10]
    most_votes_missed = sorted(rows, key=lambda r: r["votes_missed"], reverse=True)[:10]
    top_verbosity = sorted(verbosity_rows, key=lambda r: r["words_per_speech"], reverse=True)[:10]

    top_statements_2025 = sorted(
        [r for r in rows if r.get("statements_2025", 0) > 0],
        key=lambda r: r["statements_2025"],
        reverse=True,
    )[:10]

    pass_rate_rows = [r for r in rows if r["sponsored_bills"] >= 2]
    top_pass_rate = sorted(
        pass_rate_rows,
        key=lambda r: (r["passed_bills"] / r["sponsored_bills"], r["passed_bills"]),
        reverse=True,
    )[:10]

    quality_rows = [r for r in rows if r["sponsored_bills"] >= 1]
    for r in quality_rows:
        r["pass_rate_pct"] = round((r["passed_bills"] / r["sponsored_bills"]) * 100, 1)
    high_quality = sorted(quality_rows, key=lambda r: (r["pass_rate_pct"], r["passed_bills"]), reverse=True)[:10]
    high_quantity = sorted(rows, key=lambda r: (r["sponsored_bills"], r["passed_bills"]), reverse=True)[:10]

    leadership_roles = {"Chair", "Vice Chair", "Majority Leader", "Deputy Minority Whip", "Ranking Member"}
    leaders = [r for r in rows if r["committee_role"] in leadership_roles]
    members = [r for r in rows if r["committee_role"] not in leadership_roles]

    sp_per_sess = [r for r in rows if r["sessions_attended"] >= 10]
    top_speeches_per_session = sorted(sp_per_sess, key=lambda r: r["speeches_per_session"], reverse=True)[:10]
    silent_attenders = sorted(
        [r for r in rows if r["sessions_attended"] >= 20 and r["speeches"] < 100],
        key=lambda r: r["sessions_attended"],
        reverse=True,
    )[:10]

    punchy = sorted([r for r in verbosity_rows if r["words_per_speech"] < 60], key=lambda r: r["speeches"], reverse=True)[:10]

    bills_per_sess = [r for r in rows if r["sessions_attended"] >= 5 and r["sponsored_bills"] > 0]
    top_bills_per_session = sorted(bills_per_sess, key=lambda r: r["bills_per_session"], reverse=True)[:10]

    bills_per_sp = [r for r in rows if r["speeches"] >= 20 and r["sponsored_bills"] > 0]
    top_bills_per_speech = sorted(bills_per_sp, key=lambda r: r["bills_per_speech"], reverse=True)[:10]

    structural_heavy = sorted([r for r in rows if r["structural_score"] > r["debate_score"] + 5], key=lambda r: r["structural_score"], reverse=True)[:10]
    debate_heavy = sorted([r for r in rows if r["debate_score"] > r["structural_score"] + 5], key=lambda r: r["debate_score"], reverse=True)[:10]
    balanced = sorted([r for r in rows if abs(r["structural_score"] - r["debate_score"]) <= 5], key=lambda r: r["overall_score"], reverse=True)[:10]

    top_floor_leader = sorted(rows, key=lambda r: r["floor_leader_index"], reverse=True)[:10]
    top_legislative_workhorse = sorted(rows, key=lambda r: r["legislative_workhorse_index"], reverse=True)[:10]
    top_balanced = sorted(rows, key=lambda r: r["balanced_contributor"], reverse=True)[:10]

    high_bills_low_debate = sorted([r for r in rows if r["sponsored_bills"] >= 5 and r["debate_score"] < 30], key=lambda r: r["sponsored_bills"], reverse=True)[:10]
    high_motions_low_speeches = sorted([r for r in rows if r["motions_sponsored"] >= 5 and r["speeches"] < 200], key=lambda r: r["motions_sponsored"], reverse=True)[:10]
    high_words_low_score = sorted([r for r in rows if r["words_spoken"] >= 50000 and r["overall_score"] < 50], key=lambda r: r["words_spoken"], reverse=True)[:10]

    vote_heavy_low_debate = sorted([r for r in rows if r["vote_rate"] >= 90 and r["debate_score"] < 35], key=lambda r: r["vote_rate"], reverse=True)[:10]
    debate_heavy_low_vote = sorted([r for r in rows if r["debate_score"] >= 38 and r["vote_rate"] < 80], key=lambda r: r["debate_score"], reverse=True)[:10]

    words_arr = sorted([r["words_spoken"] for r in rows])
    speeches_arr = sorted([r["speeches"] for r in rows])
    for r in rows:
        r["words_percentile"] = _percentile_rank(r["words_spoken"], words_arr)
        r["speeches_percentile"] = _percentile_rank(r["speeches"], speeches_arr)
    top_words_percentile = sorted(rows, key=lambda r: r["words_percentile"], reverse=True)[:10]

    if n >= 4:
        q = max(1, n // 4)
        att_thresh = sorted([r["attendance_rate"] for r in rows], reverse=True)[q - 1]
        sp_thresh = sorted([r["speeches"] for r in rows], reverse=True)[q - 1]
        vote_thresh = sorted([r["vote_rate"] for r in rows], reverse=True)[q - 1]
        leg_thresh = sorted([r["sponsored_bills"] + r["passed_bills"] * 2 for r in rows], reverse=True)[q - 1]
        all_rounders = [
            r for r in rows
            if r["attendance_rate"] >= att_thresh
            and r["speeches"] >= sp_thresh
            and r["vote_rate"] >= vote_thresh
            and (r["sponsored_bills"] + r["passed_bills"] * 2) >= leg_thresh
        ]
        all_rounders = sorted(all_rounders, key=lambda r: r["overall_score"], reverse=True)[:10]
    else:
        all_rounders = []

    def leg_output(r):
        return r["sponsored_bills"] + r["passed_bills"] + r["amendments"]

    high_att = sorted(rows, key=lambda r: r["attendance_rate"], reverse=True)[:n // 2] if n else []
    gap_high_att_low_leg = sorted([r for r in high_att if leg_output(r) <= 2], key=lambda r: r["attendance_rate"], reverse=True)[:10]
    high_leg = sorted(rows, key=leg_output, reverse=True)[:n // 2] if n else []
    gap_low_att_high_leg = sorted([r for r in high_leg if r["attendance_rate"] < 70], key=leg_output, reverse=True)[:10]

    eff_rows = [r for r in rows if r["speeches"] >= 10]
    for r in eff_rows:
        r["efficiency"] = round((r["passed_bills"] / r["speeches"]) * 100, 2) if r["speeches"] else 0
    top_efficiency = sorted(eff_rows, key=lambda r: r["efficiency"], reverse=True)[:10]

    return {
        "attendance": top_attendance,
        "sponsored_bills": top_sponsored,
        "passed_bills": top_passed,
        "speeches": top_speeches,
        "words_spoken": top_words,
        "motions_sponsored": top_motions,
        "sessions_attended": top_sessions,
        "verbosity": top_verbosity,
        "speeches_per_session": top_speeches_per_session,
        "silent_attenders": silent_attenders,
        "punchy_speakers": punchy,
        "bills_per_session": top_bills_per_session,
        "bills_per_speech": top_bills_per_speech,
        "structural_heavy": structural_heavy,
        "debate_heavy": debate_heavy,
        "balanced_contributors": balanced,
        "floor_leader": top_floor_leader,
        "legislative_workhorse": top_legislative_workhorse,
        "balanced_index": top_balanced,
        "high_bills_low_debate": high_bills_low_debate,
        "high_words_low_score": high_words_low_score,
        "high_motions_low_speeches": high_motions_low_speeches,
        "vote_heavy_low_debate": vote_heavy_low_debate,
        "debate_heavy_low_vote": debate_heavy_low_vote,
        "words_percentile": top_words_percentile,
        "amendments": top_amendments,
        "committee_attendance": top_committee,
        "vote_rate": top_vote_rate,
        "oversight_actions": top_oversight,
        "statements_2025": top_statements_2025,
        "pass_rate": top_pass_rate,
        "county_representation": top_county_rep,
        "efficiency": top_efficiency,
        "all_rounders": all_rounders,
        "gap_high_att_low_leg": gap_high_att_low_leg,
        "gap_low_att_high_leg": gap_low_att_high_leg,
        "most_votes_missed": most_votes_missed,
        "high_quality_legislative": high_quality,
        "high_quantity_legislative": high_quantity,
        "committee_leaders": leaders,
        "committee_members": members,
    }


def build_aggregate_stats(rows):
    """Return frontier, party, grade, county, and nomination aggregate stats."""
    total_active = len(rows)
    avg_overall = round(sum(r["overall_score"] for r in rows) / total_active, 1) if total_active else 0
    avg_attendance = round(sum(r["attendance_rate"] for r in rows) / total_active, 1) if total_active else 0
    total_bills = sum(r["sponsored_bills"] for r in rows)
    total_passed = sum(r["passed_bills"] for r in rows)
    pass_rate = round((total_passed / total_bills) * 100, 1) if total_bills else 0
    total_words = sum(r["words_spoken"] for r in rows)
    total_speeches = sum(r["speeches"] for r in rows)
    total_motions = sum(r["motions_sponsored"] for r in rows)

    bins = [0] * 10
    for r in rows:
        idx = max(0, min(99, int(r["overall_score"]))) // 10
        bins[idx] += 1

    frontier_stats = {}
    for r in rows:
        f = r["frontier"]
        fs = frontier_stats.setdefault(f, {"frontier": f, "count": 0, "sum_score": 0})
        fs["count"] += 1
        fs["sum_score"] += r["overall_score"]
    for fs in frontier_stats.values():
        fs["avg_score"] = round(fs["sum_score"] / fs["count"], 1) if fs["count"] else 0
    frontier_chart = sorted(frontier_stats.values(), key=lambda x: x["avg_score"], reverse=True)

    frontier_best = {}
    for r in rows:
        f = r["frontier"]
        if f not in frontier_best or r["overall_score"] > frontier_best[f]["overall_score"]:
            frontier_best[f] = r
    best_per_frontier = sorted(frontier_best.values(), key=lambda x: (x["overall_score"], x["frontier"]), reverse=True)

    frontier_by_metric = {}
    for r in rows:
        f = r["frontier"]
        if f not in frontier_by_metric:
            frontier_by_metric[f] = {"frontier": f, "scores": [], "attendance": [], "bills": [], "speeches": [], "words": []}
        frontier_by_metric[f]["scores"].append(r["overall_score"])
        frontier_by_metric[f]["attendance"].append(r["attendance_rate"])
        frontier_by_metric[f]["bills"].append(r["sponsored_bills"] + r["passed_bills"])
        frontier_by_metric[f]["speeches"].append(r["speeches"])
        frontier_by_metric[f]["words"].append(r["words_spoken"])
    for fb in frontier_by_metric.values():
        c = len(fb["scores"])
        fb["avg_score"] = round(sum(fb["scores"]) / c, 1) if c else 0
        fb["avg_attendance"] = round(sum(fb["attendance"]) / c, 1) if c else 0
        fb["avg_bills"] = round(sum(fb["bills"]) / c, 1) if c else 0
        fb["avg_speeches"] = round(sum(fb["speeches"]) / c, 0) if c else 0
        fb["avg_words"] = round(sum(fb["words"]) / c, 0) if c else 0
    frontier_by_metric = sorted(frontier_by_metric.values(), key=lambda x: x["avg_score"], reverse=True)

    leadership_roles = {"Chair", "Vice Chair", "Majority Leader", "Deputy Minority Whip", "Ranking Member"}
    leaders = [r for r in rows if r["committee_role"] in leadership_roles]
    members = [r for r in rows if r["committee_role"] not in leadership_roles]
    committee_leadership_impact = {
        "leaders_avg": round(sum(r["overall_score"] for r in leaders) / len(leaders), 1) if leaders else 0,
        "leaders_count": len(leaders),
        "members_avg": round(sum(r["overall_score"] for r in members) / len(members), 1) if members else 0,
        "members_count": len(members),
    }

    county_perf = {}
    for r in rows:
        key = r.get("county_slug") or r["county"] or "other"
        if key not in county_perf:
            county_perf[key] = {"county": r["county"] or key, "slug": key, "scores": [], "attendance": [], "bills": []}
        county_perf[key]["scores"].append(r["overall_score"])
        county_perf[key]["attendance"].append(r["attendance_rate"])
        county_perf[key]["bills"].append(r["sponsored_bills"] + r["passed_bills"])
    for cp in county_perf.values():
        c = len(cp["scores"])
        cp["avg_score"] = round(sum(cp["scores"]) / c, 1) if c else 0
        cp["avg_attendance"] = round(sum(cp["attendance"]) / c, 1) if c else 0
        cp["avg_bills"] = round(sum(cp["bills"]) / c, 1) if c else 0
        cp["senator_count"] = c
    county_performance = sorted(county_perf.values(), key=lambda x: x["avg_score"], reverse=True)[:20]

    role_counts = {}
    role_scores = {}
    for r in rows:
        role = r["committee_role"]
        role_counts[role] = role_counts.get(role, 0) + 1
        role_scores.setdefault(role, []).append(r["overall_score"])
    committee_role_stats = [
        {
            "role": role,
            "count": role_counts[role],
            "avg_score": round(sum(role_scores[role]) / len(role_scores[role]), 1) if role_scores[role] else 0,
        }
        for role in sorted(role_counts.keys(), key=lambda r: role_counts[r], reverse=True)
    ]

    grade_counts = {}
    grade_tier_stats = {}
    for r in rows:
        g = r["grade"]
        grade_counts[g] = grade_counts.get(g, 0) + 1
        if g not in grade_tier_stats:
            grade_tier_stats[g] = {"grade": g, "count": 0, "words": [], "speeches": [], "motions": [], "structural": [], "debate": []}
        grade_tier_stats[g]["count"] += 1
        grade_tier_stats[g]["words"].append(r["words_spoken"])
        grade_tier_stats[g]["speeches"].append(r["speeches"])
        grade_tier_stats[g]["motions"].append(r["motions_sponsored"])
        grade_tier_stats[g]["structural"].append(r["structural_score"])
        grade_tier_stats[g]["debate"].append(r["debate_score"])
    for gs in grade_tier_stats.values():
        c = gs["count"]
        gs["avg_words"] = round(sum(gs["words"]) / c, 0) if c else 0
        gs["avg_speeches"] = round(sum(gs["speeches"]) / c, 0) if c else 0
        gs["avg_motions"] = round(sum(gs["motions"]) / c, 1) if c else 0
        gs["avg_structural"] = round(sum(gs["structural"]) / c, 1) if c else 0
        gs["avg_debate"] = round(sum(gs["debate"]) / c, 1) if c else 0
    grade_distribution = sorted(
        [{"grade": g, "count": c} for g, c in grade_counts.items()],
        key=lambda x: (GRADE_ORDER.get(x["grade"], 99), x["grade"]),
    )
    grade_tier_stats = sorted(grade_tier_stats.values(), key=lambda x: GRADE_ORDER.get(x["grade"], 99))

    party_stats = {}
    for r in rows:
        p = r["party"]
        if p not in party_stats:
            party_stats[p] = {"party": p, "count": 0, "scores": []}
        party_stats[p]["count"] += 1
        party_stats[p]["scores"].append(r["overall_score"])
    for ps in party_stats.values():
        ps["avg_score"] = round(sum(ps["scores"]) / len(ps["scores"]), 1) if ps["scores"] else 0
    party_performance = sorted(party_stats.values(), key=lambda x: (x["avg_score"], x["count"]), reverse=True)[:15]

    nominated = [r for r in rows if r["is_nominated"]]
    elected = [r for r in rows if not r["is_nominated"]]
    nominated_vs_elected = {
        "nominated_count": len(nominated),
        "elected_count": len(elected),
        "nom_avg_score": round(sum(r["overall_score"] for r in nominated) / len(nominated), 1) if nominated else 0,
        "elec_avg_score": round(sum(r["overall_score"] for r in elected) / len(elected), 1) if elected else 0,
        "nom_avg_att": round(sum(r["attendance_rate"] for r in nominated) / len(nominated), 1) if nominated else 0,
        "elec_avg_att": round(sum(r["attendance_rate"] for r in elected) / len(elected), 1) if elected else 0,
    }

    improving, declining = [], []
    for r in rows:
        td = r.get("trend_data") or []
        if not isinstance(td, list) or len(td) < 2:
            continue
        scores = []
        for point in td:
            if isinstance(point, dict) and "score" in point:
                scores.append(float(point["score"]))
            elif isinstance(point, (int, float)):
                scores.append(float(point))
        if len(scores) >= 2:
            r_copy = dict(r)
            r_copy["trend_direction"] = "improving" if scores[-1] > scores[0] else "declining"
            r_copy["trend_change"] = round(scores[-1] - scores[0], 1)
            if scores[-1] > scores[0]:
                improving.append(r_copy)
            else:
                declining.append(r_copy)
    top_improving = sorted(improving, key=lambda r: r["trend_change"], reverse=True)[:10]
    top_declining = sorted(declining, key=lambda r: r["trend_change"])[:10]

    return {
        "metrics": {
            "total_active": total_active,
            "avg_overall": avg_overall,
            "avg_attendance": avg_attendance,
            "total_bills": total_bills,
            "total_passed": total_passed,
            "pass_rate": pass_rate,
            "total_words": total_words,
            "total_speeches": total_speeches,
            "total_motions": total_motions,
        },
        "bins": bins,
        "frontier_chart": frontier_chart,
        "frontier_by_metric": frontier_by_metric,
        "best_per_frontier": best_per_frontier,
        "committee_leadership_impact": committee_leadership_impact,
        "county_performance": county_performance,
        "committee_role_stats": committee_role_stats,
        "grade_distribution": grade_distribution,
        "grade_tier_stats": grade_tier_stats,
        "party_performance": party_performance,
        "nominated_vs_elected": nominated_vs_elected,
        "nominated": nominated,
        "elected": elected,
        "top_improving": top_improving,
        "top_declining": top_declining,
    }
