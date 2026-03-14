"""
Update senator legislative data from external public sources.
Run: python update_legislative_from_sources.py
"""
import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance
from scorecard.engine import perf_to_engine_data, HansardEngine

# (senator_id, sponsored_bills, passed_bills, extra_updates) - from Parliament, Mzalendo, news
# extra_updates: dict of perf field overrides, e.g. {"speeches": 582}
UPDATES = [
    # Samson Cherargei: Employment (passed Senate), Livestock Bill, Constitution Amendment
    ("samson-kiprotich-cherargei", 3, 1, {}),
    # Crystal Asige: Parliament and Hansard now aligned at seven Bills, with PWD Bill passed April 2025
    ("crystal-asige", 7, 1, {}),
    # Jackson Mandago: Local Content Bill 2025; Mzalendo: 582 speeches in 13th Parliament
    ("kiplagat-jackson-mandago", 1, 0, {"speeches": 582}),
]

for row in UPDATES:
    senator_id, sponsored, passed = row[0], row[1], row[2]
    extra = row[3] if len(row) > 3 else {}
    senator = Senator.objects.filter(senator_id=senator_id).first()
    if not senator:
        print(f"Skip {senator_id}: not found")
        continue
    perf = senator.perf
    if not perf:
        print(f"Skip {senator.name}: no perf record")
        continue
    perf.sponsored_bills = sponsored
    perf.passed_bills = passed
    for k, v in extra.items():
        setattr(perf, k, v)
    perf.save()

    data = perf_to_engine_data(perf)
    res = HansardEngine.calculate(data)
    perf.overall_score = res["overall_score"]
    perf.grade = res["grade"]
    perf.structural_score = res["structural_score"]
    perf.debate_score = res["debate_score"]
    perf.save(update_fields=["overall_score", "grade", "structural_score", "debate_score"])

    print(f"Updated {senator.name}: sponsored={sponsored}, passed={passed}, score={perf.overall_score}, grade={perf.grade}")

print("Done.")
