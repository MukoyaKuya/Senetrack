"""
Update Murungi Kathuri - data from Parliament (Mzalendo).
6522 speeches in 13th Parliament; 3 sponsored bills; 1 passed (County Public Finance Laws);
19 votes recorded: 18 attended, 1 Absent (Sugar Bill).
Deputy Speaker; Chair of Liaison and Procedure and Rules committees.
"""
import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance
from scorecard.engine import perf_to_engine_data, HansardEngine

senator = Senator.objects.filter(senator_id="murungi-kathuri").first()
if senator:
    perf = senator.perf
    perf.speeches = 6522
    perf.sponsored_bills = 3
    perf.passed_bills = 1  # County Public Finance Laws (Amendment) Bill assented
    perf.total_votes = 19
    perf.attended_votes = 18  # 1 Absent (Sugar Bill)
    perf.attendance_rate = round((18 / 19) * 100, 1)
    perf.committee_role = "Chair"  # Chair of Liaison, Procedure and Rules
    perf.save()

    data = perf_to_engine_data(perf)
    res = HansardEngine.calculate(data)
    perf.overall_score = res["overall_score"]
    perf.grade = res["grade"]
    perf.structural_score = res["structural_score"]
    perf.debate_score = res["debate_score"]
    perf.save(update_fields=["overall_score", "grade", "structural_score", "debate_score"])

    print(f"Updated: {senator.name}")
    print(f"  Speeches        : {perf.speeches}")
    print(f"  Sponsored Bills : {perf.sponsored_bills}")
    print(f"  Passed Bills    : {perf.passed_bills}")
    print(f"  Votes           : {perf.attended_votes}/{perf.total_votes}")
    print(f"  Grade           : {perf.grade}")
else:
    print("Senator murungi-kathuri not found.")
