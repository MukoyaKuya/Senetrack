from typing import Dict, Any, List

class SenatorPerformanceEngine:
    """
    The 100-point Weighted Multi-Factor Analysis (WMFA) Engine.
    Calculates performance based on 5 legislative pillars.
    """
    SPEECH_BENCHMARK = 600
    WEIGHTS = {
        "participation": 0.30,
        "legislative": 0.20,
        "committee": 0.25,
        "voting": 0.20,
        "county": 0.05
    }
    
    # Weights for specific committee roles
    ROLE_WEIGHTS = {
        "Chair": 100, 
        "Majority Leader": 95,
        "Vice Chair": 85, 
        "Deputy Minority Whip": 95,
        "Ranking Member": 75, 
        "Member": 75, 
        "None": 0
    }

    @classmethod
    def calculate(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Participation (30 pts)
        speech_norm = min(data.get("speeches", 0) / cls.SPEECH_BENCHMARK, 1.0) * 100
        p1_subtotal = (speech_norm * 0.5) + (data.get("attendance_rate", 0) * 0.5)
        p1 = p1_subtotal * cls.WEIGHTS["participation"]

        # 2. Legislative (20 pts)
        # Higher base for highly active debaters even without primary bill sponsorship, 
        # but capped directly to encourage actual legislative work.
        if data.get("speeches", 0) > 500:
            leg_base = 20
        elif data.get("speeches", 0) > 100:
            leg_base = 10
        else:
            leg_base = 0
        
        p2_points = (data.get("sponsored_bills", 0) * 35) + (data.get("passed_bills", 0) * 25) + (data.get("amendments", 0) * 10)
        p2_subtotal = min(leg_base + p2_points, 100)
        p2 = (p2_subtotal / 100) * 20

        # 3. Committee (25 pts)
        role_pts = cls.ROLE_WEIGHTS.get(data.get("committee_role", "Member"), 75)
        # Boost attendance ensuring active members get higher scores than absent chairs
        p3_subtotal = (role_pts * 0.40) + (data.get("committee_attendance", 0) * 0.60) + 2
        p3 = min((p3_subtotal / 100) * 25, 25)

        # 4. Voting (20 pts)
        total_eligible = max(data.get("total_votes", 20), 1) # Prevent div by zero
        attended = min(data.get("attended_votes", 0), total_eligible)
        
        # Percentage based on their actual eligible votes
        p4 = (float(attended) / total_eligible) * 20.0

        # 5. County (5 pts)
        # Input is out of 10 natively; divide by 2 to map to 5 points (bounds checked)
        county_val = data.get("county_representation", 8.0)
        county_val = min(max(float(county_val) if county_val is not None else 8.0, 0.0), 10.0)
        p5 = county_val / 2.0

        total = round(p1 + p2 + p3 + p4 + p5)
        
        # Determine Grade (A, A-, B+, B, B-, C+, C, C-, D+, D, D-, E)
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
            "pillars": {
                "participation": round(p1, 1),
                "legislative": round(p2, 1),
                "committee": round(p3, 1),
                "voting": round(p4, 1),
                "county": round(p5, 1)
            },
            "percentages": {
                "participation": round((p1 / 30) * 100, 1),
                "legislative": round((p2 / 20) * 100, 1),
                "committee": round((p3 / 25) * 100, 1),
                "voting": round((p4 / 20) * 100, 1),
                "county": round((p5 / 5) * 100, 1)
            },
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
