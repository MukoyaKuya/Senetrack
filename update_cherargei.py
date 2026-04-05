import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance
from scorecard.engine import perf_to_engine_data, HansardEngine

senator = Senator.objects.filter(senator_id="samson-kiprotich-cherargei").first()
if senator:
    perf = senator.perf
    # Legislative: 6 bills per official Bills Tracker (updated 27.03.2026)
    # Including Employment (Amendment) Bill, Prevention of Livestock Bill, Public Service Principles Bill, etc.
    # Sources: Senate Bills Tracker PDF, Tuko, Capital FM, Parliament.
    perf.sponsored_bills = 6
    perf.passed_bills = 2  # Employment (Amendment) Bill + Public Service Principles Bill
    perf.save()

    data = perf_to_engine_data(perf)
    res = HansardEngine.calculate(data)
    perf.overall_score = res["overall_score"]
    perf.grade = res["grade"]
    perf.structural_score = res["structural_score"]
    perf.debate_score = res["debate_score"]
    perf.save(update_fields=["overall_score", "grade", "structural_score", "debate_score"])

    print(f"Updated: {senator.name}")
    print(f"  Sponsored Bills : {perf.sponsored_bills}")
    print(f"  Passed Bills    : {perf.passed_bills}")
    print(f"  Overall Score   : {perf.overall_score}")
    print(f"  Grade           : {perf.grade}")
else:
    print("Senator samson-kiprotich-cherargei not found.")
