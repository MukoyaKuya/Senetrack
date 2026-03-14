import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance

# Moses Otieno Kajwang' - data from Parliament (Mzalendo/official)
# 613 speeches total in 13th Parliament; 3 sponsored bills; 2 passed
# 17 votes recorded: 14 attended (Yes/No), 3 Absent
# Chair of County Public Accounts committee
# words_spoken: estimated ~150 words/speech for 613 speeches
senator = Senator.objects.filter(senator_id="moses-otieno-kajwang").first()
if senator:
    perf = senator.perf
    perf.speeches = 613
    perf.words_spoken = 92000  # ~150 words/speech × 613 (estimate; no official count)
    perf.sessions_attended = 80  # estimate for active senator; official count not provided
    perf.sponsored_bills = 3
    perf.passed_bills = 2
    perf.total_votes = 17
    perf.attended_votes = 14  # 3 Absent (Oct 12 2023, Oct 17 2024, Oct 29 2024)
    perf.attendance_rate = round((14 / 17) * 100, 1)
    perf.committee_role = "Chair"  # Chair of County Public Accounts committee
    perf.county_representation_score = 8.0  # 4/5 = 8/10
    perf.save()

    from scorecard.engine import perf_to_engine_data, HansardEngine
    data = perf_to_engine_data(perf)
    results = HansardEngine.calculate(data)
    perf.overall_score = results["overall_score"]
    perf.grade = results["grade"]
    perf.structural_score = results.get("structural_score", 0)
    perf.debate_score = results.get("debate_score", 0)
    perf.save(update_fields=["overall_score", "grade", "structural_score", "debate_score"])

    print(f"Updated: {senator.name}")
    print(f"  Speeches        : {perf.speeches}")
    print(f"  Sponsored Bills : {perf.sponsored_bills}")
    print(f"  Passed Bills    : {perf.passed_bills}")
    print(f"  Votes           : {perf.attended_votes}/{perf.total_votes}")
    print(f"  Attendance Rate : {perf.attendance_rate}%")
    print(f"  Committee Role  : {perf.committee_role}")
    print(f"  Overall Score   : {perf.overall_score}")
    print(f"  Grade           : {perf.grade}")
else:
    print("Senator moses-otieno-kajwang not found.")
