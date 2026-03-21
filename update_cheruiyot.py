import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance

senator = Senator.objects.filter(name__icontains="Cheruiyot").first()
if senator:
    perf = senator.perf
    perf.speeches = 2834
    perf.sponsored_bills = 18
    perf.passed_bills = 3 # Counted 3 passed (Assented or passed)
    perf.total_votes = 20
    perf.attended_votes = 20 # 0 Absent out of 20 - He voted yes/no for all instances
    perf.attendance_rate = 100.0 # based on 20/20 voting attendance
    perf.save()
    print(f"Updated {senator.name}'s performance. New speeches: {perf.speeches}, Sponsored: {perf.sponsored_bills}, Passed: {perf.passed_bills}, Total Votes: {perf.total_votes}, Attended: {perf.attended_votes}")
else:
    print("Senator not found")
