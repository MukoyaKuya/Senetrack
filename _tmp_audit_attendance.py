import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
import django; django.setup()

from django.db.models import Avg, F, FloatField
from django.db.models.functions import Cast
from scorecard.models import ParliamentaryPerformance

agg = ParliamentaryPerformance.objects.aggregate(
    db_avg=Avg('attendance_rate'),
    session_avg=Avg(Cast(F('sessions_attended'), FloatField()) / 102.0 * 100),
    vote_avg=Avg(Cast(F('attended_votes'), FloatField()) / Cast(F('total_votes'), FloatField()) * 100),
)

print(f"Average in DB (attendance_rate column): {agg['db_avg']:.2f}%")
print(f"Average based on Sessions (Plenary):    {agg['session_avg']:.2f}%")
print(f"Average based on Votes (Divisions):      {agg['vote_avg']:.2f}%")

# Check some low performers
lows = ParliamentaryPerformance.objects.values('senator__name', 'attendance_rate', 'sessions_attended').order_by('sessions_attended')[:5]
print("\nLow Performers (bottom 5 by sessions):")
for s in lows:
    print(f"{s['senator__name']}: DB Rate={s['attendance_rate']}%, Sessions={s['sessions_attended']}")
