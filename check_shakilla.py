import os, sys, django
sys.path.append(r"c:\Users\Little Human\Desktop\ReportFormv2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()
from scorecard.models import Senator
s = Senator.objects.filter(name__icontains="Shakilla").first()
if s:
    p = s.perf
    print("Name:", s.name)
    print("Score:", s.score, "| Grade:", s.grade)
    print("Speeches:", p.speeches)
    print("Sponsored Bills:", p.sponsored_bills)
    print("Passed Bills:", p.passed_bills)
    print("Total Votes:", p.total_votes, "| Attended:", p.attended_votes)
    print("Attendance Rate:", p.attendance_rate)
    print("Committee Role:", p.committee_role)
else:
    print("NOT FOUND")
