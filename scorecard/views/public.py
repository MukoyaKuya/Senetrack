from django.conf import settings
from django.shortcuts import render

from scorecard.engine import get_engine_result, perf_to_engine_data
from scorecard.models import Senator, Party
from scorecard.services.senators import get_frontier


ACTIVE_DEBATES_DEFAULT = 12


def home(request):
    """Landing/home page with action buttons."""
    senators_with_perf = Senator.objects.filter(perf__isnull=False).select_related("perf")
    total_senators = Senator.objects.count()
    total_bills = 0
    avg_attendance = 0
    if senators_with_perf.exists():
        perf_list = list(senators_with_perf)
        total_bills = sum(
            getattr(p.perf, "sponsored_bills", 0)
            + getattr(p.perf, "passed_bills", 0)
            + getattr(p.perf, "amendments", 0)
            for p in perf_list
        )
        rates = [p.perf.attendance_rate for p in perf_list]
        avg_attendance = round(sum(rates) / len(rates), 0) if rates else 0
    active_debates = getattr(settings, "ACTIVE_DEBATES", ACTIVE_DEBATES_DEFAULT)
    return render(
        request,
        "scorecard/home.html",
        {
            "total_senators": total_senators,
            "total_bills": total_bills,
            "avg_attendance": avg_attendance,
            "active_debates": active_debates,
        },
    )


def senator_list(request):
    """List of all senators with pagination."""
    senators_qs = Senator.objects.select_related("perf", "county_fk").order_by("name")
    party_logos = {p.name.strip(): p.logo.url for p in Party.objects.filter(logo__isnull=False).only("name", "logo")}
    PLACEHOLDER_NAME = "{{ senator.name }}"
    senator_list_data = []
    for s in senators_qs:
        name = s.senator_id.replace("-", " ").title() if s.name == PLACEHOLDER_NAME else s.name
        county = getattr(getattr(s, "county_fk", None), "name", "—")
        image_url = s.image.url if s.image else (s.image_url or "")
        res = get_engine_result(getattr(s, "perf", None))
        overall_score = res["overall_score"] if res else 0
        frontier = get_frontier(s)
        party_name = (s.party or "").strip()
        party_logo_url = party_logos.get(party_name) if party_name else None
        senator_list_data.append(
            {
                "senator_id": s.senator_id,
                "name": name,
                "county": county,
                "nomination": getattr(s, "nomination", None) or "",
                "party": s.party,
                "party_logo_url": party_logo_url,
                "image_url": image_url,
                "overall_score": overall_score,
                "is_deceased": getattr(s, "is_deceased", False),
                "is_still_computing": getattr(s, "is_still_computing", False),
                "frontier": frontier,
            }
        )

    return render(
        request,
        "scorecard/index.html",
        {
            "senators": senator_list_data,
        },
    )


def about(request):
    """About page with performance engine documentation."""
    return render(request, "scorecard/about.html")

