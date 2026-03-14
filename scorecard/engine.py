from math import log
from typing import Dict, Any, List, Optional


def perf_to_engine_data(perf) -> Optional[Dict[str, Any]]:
    """Convert ParliamentaryPerformance instance to engine input dict. Returns None if perf is None."""
    if perf is None:
        return None
    data = {
        "speeches": getattr(perf, "speeches", 0) or 0,
        "attendance_rate": getattr(perf, "attendance_rate", 0) or 0,
        "sponsored_bills": getattr(perf, "sponsored_bills", 0) or 0,
        "passed_bills": getattr(perf, "passed_bills", 0) or 0,
        "amendments": getattr(perf, "amendments", 0) or 0,
        "committee_role": getattr(perf, "committee_role", "Member") or "Member",
        "committee_attendance": getattr(perf, "committee_attendance", 0) or 0,
        "total_votes": getattr(perf, "total_votes", 20) or 20,
        "attended_votes": getattr(perf, "attended_votes", 0) or 0,
        "oversight_actions": getattr(perf, "oversight_actions", 0) or 0,
        "county_representation": getattr(perf, "county_representation_score", 0) or 0,
    }
    # Hansard 2025 fields
    data["words_spoken"] = getattr(perf, "words_spoken", 0) or 0
    data["motions_sponsored"] = getattr(perf, "motions_sponsored", 0) or 0
    data["sessions_attended"] = getattr(perf, "sessions_attended", 0) or 0
    # Statements Tracker fields (e.g. up to Nov 2025)
    data["statements_2025"] = getattr(perf, "statements_2025", 0) or 0
    # Nomination flag (for small bonus for nominated senators)
    is_nominated = False
    try:
        senator = getattr(perf, "senator", None)
        if senator is not None:
            nomination = getattr(senator, "nomination", "") or ""
            is_nominated = bool(nomination.strip())
    except Exception:
        is_nominated = False
    data["is_nominated"] = is_nominated
    return data


def _log_score(val: float, max_val: float, pts: float) -> float:
    """Log scaling: Score = (log(1+val)/log(1+max)) * Pts. Returns 0 if max_val <= 0."""
    if max_val <= 0:
        return 0.0
    val = max(0, float(val))
    return (log(1 + val) / log(1 + max_val)) * pts


# Hansard 2025 max values (from report)
HANSARD_2025_MAX = {
    "words": 133_532,
    "speeches": 3_269,
    "motions": 27,
    "bills": 18,
    "sessions": 102,
}


class HansardEngine:
    """
    Hansard 2025 Performance Engine.
    Structural (55 pts): Voting Reliability (25), Plenary Attendance (20), Bills Sponsored (10).
    Debate (45 pts): Speech Volume (20), Speech Frequency (15), Statements/Motions (10).
    Uses log scaling for high-variance metrics.
    """

    # Grading: (min_pct, grade, grade_points)
    GRADE_TABLE = [
        (80, "A", 12),
        (75, "A-", 11),
        (70, "B+", 10),
        (65, "B", 9),
        (60, "B-", 8),
        (55, "C+", 7),
        (50, "C", 6),
        (45, "C-", 5),
        (40, "D+", 4),
        (35, "D", 3),
        (30, "D-", 2),
        (0, "E", 1),
    ]

    @classmethod
    def calculate(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate score from Hansard/Mzalendo data.
        Expects: attended_votes, total_votes, sessions_attended, sponsored_bills,
                 words_spoken, speeches, motions_sponsored.
        """
        total_votes = max(data.get("total_votes", 0) or 0, 1)
        attended_votes = min(data.get("attended_votes", 0) or 0, total_votes)
        sessions_attended = data.get("sessions_attended", 0) or 0
        sponsored_bills = data.get("sponsored_bills", 0) or 0
        words_spoken = data.get("words_spoken", 0) or 0
        speeches = data.get("speeches", 0) or 0
        motions = data.get("motions_sponsored", 0) or 0
        statements_2025 = data.get("statements_2025", 0) or 0
        is_nominated = bool(data.get("is_nominated"))

        max_vals = HANSARD_2025_MAX

        # Structural (55 pts)
        voting_pts = (attended_votes / total_votes) * 25.0
        plenary_pts = (sessions_attended / max_vals["sessions"]) * 20.0 if max_vals["sessions"] else 0
        bills_pts = _log_score(sponsored_bills, max_vals["bills"], 10.0)
        # Small boost for nominated senators so strong bill sponsors like Crystal Asige
        # are not penalized relative to long-serving county senators.
        if is_nominated and bills_pts > 0:
            bills_pts = min(bills_pts * 1.1, 10.0)
        structural_score = voting_pts + plenary_pts + bills_pts

        # Debate (45 pts)
        words_pts = _log_score(words_spoken, max_vals["words"], 20.0)
        speeches_pts = _log_score(speeches, max_vals["speeches"], 15.0)
        motions_pts = _log_score(motions, max_vals["motions"], 10.0)
        debate_score = words_pts + speeches_pts + motions_pts

        # Statements bonus (up to 3 pts, participation quality signal from Statements Tracker)
        # Use a conservative cap so statements can't overpower attendance/speeches.
        STATEMENTS_MAX_2025 = 30.0  # adjust if tracker shows a different natural max
        if statements_2025 and STATEMENTS_MAX_2025 > 0:
            s_clamped = min(float(statements_2025), STATEMENTS_MAX_2025)
            statements_bonus = (s_clamped / STATEMENTS_MAX_2025) * 3.0
        else:
            statements_bonus = 0.0

        # County representation (5 pts, scale 0–10)
        county_score = data.get("county_representation", 0) or 0
        county_pts = min(max(float(county_score), 0.0), 10.0) / 10.0 * 5.0

        overall = round(structural_score + debate_score + county_pts + statements_bonus, 2)
        pct = overall  # 0-100

        grade = "E"
        grade_points = 1
        for min_pct, g, gp in cls.GRADE_TABLE:
            if pct >= min_pct:
                grade = g
                grade_points = gp
                break

        return {
            "overall_score": overall,
            "grade": grade,
            "grade_points": grade_points,
            "structural_score": round(structural_score, 2),
            "debate_score": round(debate_score, 2),
            "pillars": {
                "voting": round(voting_pts, 2),
                "plenary": round(plenary_pts, 2),
                "bills": round(bills_pts, 2),
                "words": round(words_pts, 2),
                "speeches": round(speeches_pts, 2),
                "motions": round(motions_pts, 2),
                "county": round(county_pts, 2),
            },
            "extras": {
                "statements_bonus": round(statements_bonus, 2),
                "statements_2025": int(statements_2025 or 0),
            },
        }


def _hansard_to_template_pillars(hansard_pillars: Dict[str, float]) -> Dict[str, float]:
    """
    Map Hansard 2025 pillars to template format (participation, legislative, voting, committee, county).
    Hansard: voting(25), plenary(20), bills(10), words(20), speeches(15), motions(10).
    Template: participation(30), legislative(20), voting(20), committee(25), county(5).
    """
    v = hansard_pillars.get
    plenary = v("plenary", 0) or 0
    speeches = v("speeches", 0) or 0
    words = v("words", 0) or 0
    motions = v("motions", 0) or 0
    bills = v("bills", 0) or 0
    voting = v("voting", 0) or 0
    # participation(30) <- plenary + speeches (35 pts total, scale to 30)
    participation = (plenary + speeches) * (30 / 35) if (plenary or speeches) else 0
    # legislative(20) <- bills (10 pts, double)
    legislative = min(bills * 2, 20)
    # voting(20) <- voting (25 pts, scale to 20)
    voting_scaled = voting * (20 / 25) if voting else 0
    # committee(25) <- words + motions (30 pts total, scale to 25)
    committee = (words + motions) * (25 / 30) if (words or motions) else 0
    county = hansard_pillars.get("county", 0) or 0
    return {
        "participation": round(participation, 1),
        "legislative": round(legislative, 1),
        "voting": round(voting_scaled, 1),
        "committee": round(committee, 1),
        "county": round(county, 1),
    }


def get_engine_result(perf) -> Optional[Dict[str, Any]]:
    """
    Get performance result. Prefers HansardEngine when Hansard data exists
    (words_spoken or sessions_attended or motions_sponsored), else SenatorPerformanceEngine.
    """
    data = perf_to_engine_data(perf)
    if not data:
        return None
    # Use stored scores if already calculated by Hansard
    has_hansard_data = (
        (data.get("words_spoken") or 0) > 0
        or (data.get("sessions_attended") or 0) > 0
        or (data.get("motions_sponsored") or 0) > 0
    )
    if perf and getattr(perf, "overall_score", None) and getattr(perf, "grade", None):
        stored = float(perf.overall_score or 0)
        if stored > 0 and has_hansard_data:
            # Compute pillars from Hansard data for display
            res = HansardEngine.calculate(data)
            pillars = _hansard_to_template_pillars(res.get("pillars", {}))
            return {
                "overall_score": stored,
                "grade": perf.grade or "—",
                "grade_text": "",
                "pillars": pillars,
                "percentages": {},
                "insights": {"strengths": [], "improvements": []},
            }
    # Prefer Hansard when we have the data
    if has_hansard_data:
        res = HansardEngine.calculate(data)
        pillars = _hansard_to_template_pillars(res.get("pillars", {}))
        return {
            "overall_score": res["overall_score"],
            "grade": res["grade"],
            "grade_text": "",
            "pillars": pillars,
            "percentages": {},
            "insights": {"strengths": [], "improvements": []},
        }
    return SenatorPerformanceEngine.calculate(data)


class SenatorPerformanceEngine:
    """
    Legacy 100-point Weighted Multi-Factor Analysis (WMFA) Engine.
    Used when Hansard data is not available.
    """
    SPEECH_BENCHMARK = 600
    WEIGHTS = {
        "participation": 0.30,
        "legislative": 0.20,
        "committee": 0.25,
        "voting": 0.20,
        "county": 0.05
    }
    ROLE_WEIGHTS = {
        "Chair": 100, "Majority Leader": 95, "Vice Chair": 85,
        "Deputy Minority Whip": 95, "Ranking Member": 75, "Member": 75, "None": 0
    }

    @classmethod
    def calculate(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        speech_norm = min(data.get("speeches", 0) / cls.SPEECH_BENCHMARK, 1.0) * 100
        p1_subtotal = (speech_norm * 0.5) + (data.get("attendance_rate", 0) * 0.5)
        p1 = p1_subtotal * cls.WEIGHTS["participation"]

        if data.get("speeches", 0) > 500:
            leg_base = 20
        elif data.get("speeches", 0) > 100:
            leg_base = 10
        else:
            leg_base = 0
        p2_points = (data.get("sponsored_bills", 0) * 35) + (data.get("passed_bills", 0) * 25) + (data.get("amendments", 0) * 10)
        p2_subtotal = min(leg_base + p2_points, 100)
        p2 = (p2_subtotal / 100) * 20

        role_pts = cls.ROLE_WEIGHTS.get(data.get("committee_role", "Member"), 75)
        p3_subtotal = (role_pts * 0.40) + (data.get("committee_attendance", 0) * 0.60) + 2
        p3 = min((p3_subtotal / 100) * 25, 25)

        total_eligible = max(data.get("total_votes", 20), 1)
        attended = min(data.get("attended_votes", 0), total_eligible)
        p4 = (float(attended) / total_eligible) * 20.0

        county_val = data.get("county_representation", 8.0)
        county_val = min(max(float(county_val) if county_val is not None else 8.0, 0.0), 10.0)
        p5 = county_val / 2.0

        total = round(p1 + p2 + p3 + p4 + p5)

        if data.get("attendance_rate", 0) < 0:
            return {
                "overall_score": 0,
                "grade": "NEW",
                "grade_text": "STILL COMPUTING",
                "pillars": {"participation": 0.0, "legislative": 0.0, "committee": 0.0, "voting": 0.0, "county": 0.0},
                "percentages": {},
                "insights": {"strengths": ["Newly appointed Senator, accumulating data"], "improvements": ["Awaiting initial performance analytics"]}
            }

        # Small leadership bonus for legacy engine: reward Senators holding key roles
        # such as Chair, Majority Leader, Deputy Minority Whip, Ranking Member.
        # This mirrors the spirit of the nominated-senator tweak: a gentle nudge,
        # not a complete reshuffle of rankings.
        leadership_roles = {"Chair", "Majority Leader", "Deputy Minority Whip", "Ranking Member", "Vice Chair"}
        if (data.get("committee_role") or "Member") in leadership_roles:
            total = min(total + 2, 100)

        if total >= 90: grade, text = "A", "OUTSTANDING"
        elif total >= 85: grade, text = "A-", "EXCELLENT"
        elif total >= 80: grade, text = "B+", "VERY GOOD"
        elif total >= 75: grade, text = "B", "GOOD"
        elif total >= 70: grade, text = "B-", "ABOVE AVERAGE"
        elif total >= 65: grade, text = "C+", "FAIRLY GOOD"
        elif total >= 60: grade, text = "C", "AVERAGE"
        elif total >= 55: grade, text = "C-", "BELOW AVERAGE"
        elif total >= 50: grade, text = "D+", "MARGINAL"
        elif total >= 45: grade, text = "D", "POOR"
        elif total >= 40: grade, text = "D-", "VERY POOR"
        else: grade, text = "E", "FAIL"

        return {
            "overall_score": total,
            "grade": grade,
            "grade_text": text,
            "pillars": {"participation": round(p1, 1), "legislative": round(p2, 1), "committee": round(p3, 1), "voting": round(p4, 1), "county": round(p5, 1)},
            "percentages": {},
            "insights": cls._get_insights(p1, p2, p3, p4)
        }

    @staticmethod
    def _get_insights(p1, p2, p3, p4):
        strengths, improvements = [], []
        if p1 >= 25: strengths.append("Excellent Plenary Participation")
        elif p1 < 15: improvements.append("Needs better attendance in House Debates")
        if p2 >= 15: strengths.append("Strong Legislative Output (Bills/Amendments)")
        elif p2 < 8: improvements.append("Should sponsor original legislation or amendments")
        if p3 >= 20: strengths.append("Highly Active in Committee Work")
        elif p3 < 15: improvements.append("Increase Committee Attendance/Engagement")
        if p4 >= 18: strengths.append("Exceptional Voting Record")
        elif p4 < 12: improvements.append("Improve presence during plenary voting")
        return {
            "strengths": strengths if strengths else ["Consistent performer across indicators"],
            "improvements": improvements if improvements else ["Maintain current legislative momentum"]
        }
