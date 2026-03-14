import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance

senator = Senator.objects.filter(name__icontains="Onyonka").first()
if senator:
    perf = senator.perf
    perf.speeches = 415
    perf.sponsored_bills = 0
    perf.passed_bills = 0
    perf.total_votes = 20
    perf.attended_votes = 15
    perf.attendance_rate = 75.0 # based on voting attendance 15/20
    perf.save()
    print(f"Updated {senator.name}'s performance. New speeches: {perf.speeches}, Sponsored: {perf.sponsored_bills}, Total Votes: {perf.total_votes}, Attended: {perf.attended_votes}")
else:
    print("Senator not found")
