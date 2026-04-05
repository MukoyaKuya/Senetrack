import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
import django; django.setup()

from scorecard.models import Senator

for sid in ['moses-otieno-kajwang', 'samson-kiprotich-cherargei', 'sifuna-edwin', 'crystal-asige']:
    s = Senator.objects.select_related('perf').get(senator_id=sid)
    p = s.perf
    print(f"{s.name}: {p.overall_score} ({p.grade}), Speeches: {p.speeches}, Bills/Passed: {p.sponsored_bills}/{p.passed_bills}")
