# Trigger reload 2
from django.shortcuts import render, get_object_or_404
from .models import Senator, ParliamentaryPerformance
from .engine import SenatorPerformanceEngine
import django.http

def senator_list(request):
    """List of all senators."""
    senators = Senator.objects.all()
    # Replace placeholder strings that may have been stored in the DB
    PLACEHOLDER_NAME = "{{ senator.name }}"
    PLACEHOLDER_COUNTY = "{{ senator.county }}"
    senator_list = []
    for s in senators:
        name = s.senator_id.replace("-", " ").title() if s.name == PLACEHOLDER_NAME else s.name
        county = "—" if s.county == PLACEHOLDER_COUNTY else s.county
        image_url = s.image.url if s.image else (s.image_url or "")
        
        # Calculate scores dynamically for list view
        perf = getattr(s, 'perf', None)
        if perf:
            res = SenatorPerformanceEngine.calculate({
                "speeches": perf.speeches,
                "attendance_rate": perf.attendance_rate,
                "sponsored_bills": perf.sponsored_bills,
                "passed_bills": perf.passed_bills,
                "amendments": perf.amendments,
                "committee_role": perf.committee_role,
                "committee_attendance": perf.committee_attendance,
                "total_votes": perf.total_votes,
                "attended_votes": perf.attended_votes,
                "oversight_actions": perf.oversight_actions,
                "county_representation": perf.county_representation_score,
            })
            grade = res['grade']
            overall_score = res['overall_score']
        else:
            grade = "—"
            overall_score = 0
            
        senator_list.append({
            "senator_id": s.senator_id,
            "name": name,
            "county": county,
            "nomination": getattr(s, 'nomination', None) or '',
            "party": s.party,
            "image_url": image_url,
            "grade": grade,
            "overall_score": overall_score,
        })
    return render(request, 'scorecard/index.html', {'senators': senator_list})

def senator_detail(request, senator_id):
    """Main dashboard page."""
    senator = get_object_or_404(Senator, senator_id=senator_id)
    
    # Calculate performance for the default engine (parliamentary)
    perf = getattr(senator, 'perf', None)
    if perf:
        results = SenatorPerformanceEngine.calculate({
            "speeches": perf.speeches,
            "attendance_rate": perf.attendance_rate,
            "sponsored_bills": perf.sponsored_bills,
            "passed_bills": perf.passed_bills,
            "amendments": perf.amendments,
            "committee_role": perf.committee_role,
            "committee_attendance": perf.committee_attendance,
            "total_votes": perf.total_votes,
            "attended_votes": perf.attended_votes,
            "oversight_actions": perf.oversight_actions,
            "county_representation": perf.county_representation_score,
        })
    else:
        results = {
            "overall_score": 0,
            "grade": "—",
            "grade_text": "No data",
            "pillars": {"participation": 0, "legislative": 0, "voting": 0, "committee": 0, "county": 0},
            "percentages": {"participation": 0, "legislative": 0, "voting": 0, "committee": 0, "county": 0},
            "insights": {"strengths": ["Performance data not yet available"], "improvements": []},
        }
    
    # Compute national rank, attendance rank, and national average attendance
    national_rank = None
    attendance_rank = None
    national_avg_attendance = None
    total_senators = 0
    senators_with_perf = Senator.objects.filter(perf__isnull=False).select_related('perf')
    total_senators = senators_with_perf.count()

    if total_senators > 0:
        rates = [s.perf.attendance_rate for s in senators_with_perf]
        national_avg_attendance = round(sum(rates) / len(rates), 1)

    if perf and total_senators > 0:
        # Build list of (senator_id, overall_score, attendance_rate)
        scores = []
        for s in senators_with_perf:
            r = SenatorPerformanceEngine.calculate({
                "speeches": s.perf.speeches,
                "attendance_rate": s.perf.attendance_rate,
                "sponsored_bills": s.perf.sponsored_bills,
                "passed_bills": s.perf.passed_bills,
                "amendments": s.perf.amendments,
                "committee_role": s.perf.committee_role,
                "committee_attendance": s.perf.committee_attendance,
                "total_votes": s.perf.total_votes,
                "attended_votes": s.perf.attended_votes,
                "oversight_actions": s.perf.oversight_actions,
                "county_representation": s.perf.county_representation_score,
            })
            scores.append((s.senator_id, r['overall_score'], s.perf.attendance_rate))
        
        # Sort by overall_score desc (rank 1 = best), then by attendance desc
        scores_by_overall = sorted(scores, key=lambda x: (-x[1], -x[2]))
        scores_by_attendance = sorted(scores, key=lambda x: -x[2])
        
        for i, (sid, _, _) in enumerate(scores_by_overall, 1):
            if sid == senator_id:
                national_rank = i
                break
        for i, (sid, _, _) in enumerate(scores_by_attendance, 1):
            if sid == senator_id:
                attendance_rank = i
                break
    
    # Bills in committee (sponsored but not yet passed)
    bills_in_committee = 0
    if perf:
        bills_in_committee = max(0, perf.sponsored_bills - perf.passed_bills)

    # Attendance heatmap: senators sorted by attendance (best first), with is_current flag
    attendance_heatmap = []
    if total_senators > 0:
        sorted_by_attendance = sorted(
            [(s.senator_id, s.perf.attendance_rate, s.name) for s in senators_with_perf],
            key=lambda x: -x[1]
        )
        for sid, rate, name in sorted_by_attendance:
            attendance_heatmap.append({
                "senator_id": sid,
                "rate": round(rate, 1),
                "name": name,
                "is_current": sid == senator_id,
            })

    # Quotes period label from most recent quote date (Early/Mid/Late + year)
    latest_quote = senator.quotes.order_by("-date").first()
    if latest_quote:
        m = latest_quote.date.month
        y = latest_quote.date.year
        if m <= 3:
            quotes_period = f"Early {y}"
        elif m <= 6:
            quotes_period = f"Mid {y}"
        else:
            quotes_period = f"Late {y}"
    else:
        quotes_period = ""

    return render(request, 'scorecard/scorecard.html', {
        'senator': senator,
        'results': results,
        'national_rank': national_rank,
        'attendance_rank': attendance_rank,
        'total_senators': total_senators,
        'bills_in_committee': bills_in_committee,
        'quotes_period': quotes_period,
        'national_avg_attendance': national_avg_attendance,
        'has_national_avg': national_avg_attendance is not None,
        'attendance_heatmap': attendance_heatmap,
    })

def get_engine_partial(request, senator_id, engine_type):
    """HTMX fragment endpoint."""
    senator = get_object_or_404(Senator, senator_id=senator_id)
    
    if engine_type == "parliamentary":
        perf = get_object_or_404(ParliamentaryPerformance, senator=senator)
        results = SenatorPerformanceEngine.calculate({
            "speeches": perf.speeches,
            "attendance_rate": perf.attendance_rate,
            "sponsored_bills": perf.sponsored_bills,
            "passed_bills": perf.passed_bills,
            "amendments": perf.amendments,
            "committee_role": perf.committee_role,
            "committee_attendance": perf.committee_attendance,
            "total_votes": perf.total_votes,
            "attended_votes": perf.attended_votes,
            "oversight_actions": perf.oversight_actions,
            "county_representation": perf.county_representation_score,
        })
        
        context = {
            'results': results,
            'perf': perf,
            'missed_votes': max(0, perf.total_votes - perf.attended_votes),
            'dash_array': f"{(results['pillars']['committee'] / 25) * 251.2} 251.2"
        }
        return render(request, 'partials/parliamentary_engine.html', context)
        
    return render(request, 'partials/placeholder.html', {'type': engine_type})
