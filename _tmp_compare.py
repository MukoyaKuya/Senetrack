import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
import django; django.setup()

from scorecard.models import Senator
from scorecard.engine import perf_to_engine_data, HansardEngine

for sid in ['crystal-asige', 'joyce-chepkoech-korir']:
    s = Senator.objects.select_related('perf').get(senator_id=sid)
    p = s.perf
    d = perf_to_engine_data(p)
    r = HansardEngine.calculate(d)
    print(f"\n=== {s.name} ===")
    print(f"DB stored score: {p.overall_score}, grade: {p.grade}")
    print(f"Recalculated score: {r['overall_score']}, grade: {r['grade']}")
    print(f"Structural: {r['structural_score']}, Debate: {r['debate_score']}")
    print(f"Pillars: {r['pillars']}")
    print(f"Extras: {r['extras']}")
    print(f"Raw data: speeches={d['speeches']}, words={d['words_spoken']}, sessions={d['sessions_attended']}, motions={d['motions_sponsored']}, bills={d['sponsored_bills']}, votes={d['attended_votes']}/{d['total_votes']}, nominated={d['is_nominated']}")
