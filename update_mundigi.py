import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance

senator = Senator.objects.filter(name__icontains="Mundigi").first()
if senator:
    perf = senator.perf
    perf.speeches = 495
    perf.sponsored_bills = 0
    perf.passed_bills = 0
    perf.total_votes = 20
    perf.attended_votes = 19 # 1 absent out of 20
    perf.attendance_rate = 95.0 # based on 19/20 voting attendance
    perf.save()
    print(f"Updated {senator.name}'s performance. New speeches: {perf.speeches}, Sponsored: {perf.sponsored_bills}, Total Votes: {perf.total_votes}, Attended: {perf.attended_votes}")
else:
    print("Senator not found")
