import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance
from scorecard.engine import SenatorPerformanceEngine

senator = Senator.objects.filter(name__icontains="Shakilla").first()
if senator:
    perf = senator.perf

    # --- Raw parliamentary data (from Mzalendo) ---
    perf.speeches = 697               # Total speeches in 13th Parliament
    perf.sponsored_bills = 0          # No sponsored bills
    perf.passed_bills = 0             # No passed bills
    perf.amendments = 0               # No amendments recorded
    perf.total_votes = 20             # 20 recorded votes
    perf.attended_votes = 11          # 11 "No" votes = attended; 9 = Absent
    perf.attendance_rate = 55.0       # 11/20 = 55%
    perf.committee_role = "Member"    # Member of Finance & Budget, ICT, Powers & Privileges, Senate Business
    perf.save()

    # --- Re-run the scoring engine to verify computed results ---
    from scorecard.engine import perf_to_engine_data
    data = perf_to_engine_data(perf)
    results = SenatorPerformanceEngine.calculate(data)

    print(f"Updated: {senator.name}")
    print(f"  Speeches        : {perf.speeches}")
    print(f"  Sponsored Bills : {perf.sponsored_bills}")
    print(f"  Passed Bills    : {perf.passed_bills}")
    print(f"  Votes           : {perf.attended_votes}/{perf.total_votes}")
    print(f"  Attendance Rate : {perf.attendance_rate}%")
    print(f"  Committee Role  : {perf.committee_role}")
    print(f"  Computed Score  : {results['overall_score']}")
    print(f"  Grade           : {results['grade']} - {results['grade_text']}")
    print(f"  Pillars         : {results['pillars']}")
else:
    print("❌ Senator not found — check that 'Shakilla' matches a record in the DB.")
