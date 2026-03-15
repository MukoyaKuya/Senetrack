from pathlib import Path

from django.conf import settings
from django.db.models import Avg, Count, F, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page

from scorecard.models import ParliamentaryPerformance, Senator, Party
from scorecard.services.senators import get_frontier


ACTIVE_DEBATES_DEFAULT = 12
CACHE_PAGE_SENATORS = 180  # 3 min
CACHE_PAGE_HOME = 300      # 5 min


@cache_page(CACHE_PAGE_HOME)
def home(request):
    """Landing/home page with action buttons."""
    total_senators = Senator.objects.count()
    agg = ParliamentaryPerformance.objects.aggregate(
        total_bills=Sum(F("sponsored_bills") + F("passed_bills") + F("amendments")),
        avg_att=Avg("attendance_rate"),
        cnt=Count("id"),
    )
    total_bills = agg["total_bills"] or 0
    avg_attendance = round(agg["avg_att"] or 0, 0) if agg["cnt"] else 0
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


@cache_page(CACHE_PAGE_SENATORS)
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
        perf = getattr(s, "perf", None)
        overall_score = (perf.overall_score or 0) if perf else 0
        grade = (perf.grade or "—") if perf else "—"
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
                "grade": grade,
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


def service_worker(request):
    """Serve the service worker at /sw.js for PWA scope (root)."""
    path = Path(settings.BASE_DIR) / "scorecard" / "static" / "scorecard" / "sw.js"
    if not path.exists():
        return HttpResponse("", status=404)
    return HttpResponse(path.read_bytes(), content_type="application/javascript")

