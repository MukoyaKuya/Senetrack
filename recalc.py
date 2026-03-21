import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from scorecard.models import ParliamentaryPerformance
from scorecard.engine import SenatorPerformanceEngine

count = 0
for perf in ParliamentaryPerformance.objects.all():
    current = perf.senator.perf
    data = {
        'speeches': current.speeches,
        'attendance_rate': current.attendance_rate,
        'sponsored_bills': current.sponsored_bills,
        'passed_bills': current.passed_bills,
        'amendments': current.amendments,
        'committee_role': current.committee_role,
        'committee_attendance': current.committee_attendance,
        'total_votes': current.total_votes,
        'attended_votes': current.attended_votes,
        'county_representation': current.county_representation_score
    }
    results = SenatorPerformanceEngine.calculate(data)
    
    # Update Senator model
    senator = perf.senator
    senator.score = results['overall_score']
    senator.grade = results['grade']
    senator.save()
    
    count += 1
    
print(f"Successfully mapped {count} Senators with 1-to-1 Voting metric.")
