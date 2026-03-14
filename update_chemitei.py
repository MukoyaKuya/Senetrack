import os
import sys
import django

sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance

senator = Senator.objects.filter(name__icontains="Kiprono Chemitei").first()
if senator:
    perf = senator.perf
    # Set negative attendance_rate as a flag for "NEW STILL COMPUTING"
    perf.attendance_rate = -1.0 
    perf.speeches = 0
    perf.sponsored_bills = 0
    perf.passed_bills = 0
    perf.total_votes = 0
    perf.attended_votes = 0
    perf.save()
    print(f"Updated {senator.name}'s performance. Flagged as NEW.")
else:
    print("Senator not found")
