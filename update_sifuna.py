import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance

senator = Senator.objects.filter(name__icontains="Sifuna").first()
if senator:
    perf = senator.perf
    perf.speeches = 1658
    perf.sponsored_bills = 3
    perf.passed_bills = 0 # (They are in committee, passed but forwarded to NA, or in mediation)
    perf.total_votes = 20
    perf.attended_votes = 18 # Abstained is still attended, only 'Absent' counts against attendance. 2 Absents out of 20
    perf.attendance_rate = 90.0 # based on 18/20 voting attendance
    perf.save()
    print(f"Updated {senator.name}'s performance. New speeches: {perf.speeches}, Sponsored: {perf.sponsored_bills}, Total Votes: {perf.total_votes}, Attended: {perf.attended_votes}")
else:
    print("Senator not found")
