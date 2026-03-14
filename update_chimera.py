import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance

senator = Senator.objects.filter(name__icontains="Chimera").first()
if senator:
    perf = senator.perf
    perf.speeches = 189
    perf.sponsored_bills = 2
    perf.passed_bills = 0 # 1 in committee, 1 withdrawn
    perf.total_votes = 11
    perf.attended_votes = 11 # 0 Absent out of 11 recorded votes
    perf.attendance_rate = 100.0 # based on 11/11 voting attendance
    perf.save()
    print(f"Updated {senator.name}'s performance. New speeches: {perf.speeches}, Sponsored: {perf.sponsored_bills}, Passed: {perf.passed_bills}, Total Votes: {perf.total_votes}, Attended: {perf.attended_votes}")
else:
    print("Senator not found")
