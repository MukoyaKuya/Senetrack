import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
import django; django.setup()

from scorecard.models import Senator

ids = ['moses-otieno-kajwang', 'crystal-asige', 'vincent-cheburet-kiprono-chemitei', 'consolata-wakwabubi']
for sid in ids:
    try:
        s = Senator.objects.select_related('perf').get(senator_id=sid)
        p = s.perf
        print(f"{s.name}: {p.overall_score} ({p.grade}), Speeches: {p.speeches}, Sessions: {p.sessions_attended}")
    except:
        print(f"Not found: {sid}")
