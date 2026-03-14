"""
Update Stewart Mwachiru Shadrack Madzayo - data from Parliament (Mzalendo).
766 speeches in 13th Parliament; 8 sponsored bills; Minority Leader.
18 votes recorded: 16 attended, 2 Absent (Social Health Insurance, Business Laws).
"""
import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance
from scorecard.engine import perf_to_engine_data, HansardEngine

senator = Senator.objects.filter(senator_id="stewart-mwachiru-shadrack-madzayo").first()
if senator:
    perf = senator.perf
    perf.speeches = 766
    perf.sponsored_bills = 8
    perf.total_votes = 18
    perf.attended_votes = 16  # 2 Absent (Social Health Insurance, Business Laws)
    perf.attendance_rate = round((16 / 18) * 100, 1)
    perf.committee_role = "Minority Leader"
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
    print(f"  Votes           : {perf.attended_votes}/{perf.total_votes}")
    print(f"  Committee Role  : {perf.committee_role}")
    print(f"  Grade           : {perf.grade}")
else:
    print("Senator stewart-mwachiru-shadrack-madzayo not found.")
