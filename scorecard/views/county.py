from django.http import Http404
from django.shortcuts import get_object_or_404, render

from scorecard.engine import get_engine_result, perf_to_engine_data
from scorecard.models import County, Senator
from scorecard.security import sanitize_county_slug


def county_list(request):
    """Counties browse page with 47 county cards."""
    # Hide the synthetic "Nominated (Nationwide)" county from the public list
    counties = County.objects.exclude(slug="nominated").only("name", "slug", "region", "logo", "order").order_by("order", "name")
    return render(request, "scorecard/counties.html", {"counties": counties})


def county_detail(request, slug):
    """County profile page with senator(s) and county info."""
    clean_slug = sanitize_county_slug(slug)
    if clean_slug is None:
        raise Http404("Invalid county identifier")
    county = get_object_or_404(
        County.objects.prefetch_related("images", "senators__perf"),
        slug=clean_slug,
    )

    matched = list(county.senators.select_related("perf").order_by("name"))
    senator_list_data = []
    for s in matched:
        res = get_engine_result(getattr(s, "perf", None))
        if res:
            grade = res["grade"]
            overall_score = res["overall_score"]
        else:
            grade = "—"
            overall_score = 0
        senator_list_data.append(
            {
                "senator_id": s.senator_id,
                "name": s.name,
                "county": county.name,
                "party": s.party,
                "image_url": s.image.url if s.image else (s.image_url or ""),
                "grade": grade,
                "overall_score": overall_score,
            }
        )
    first_senator = senator_list_data[0] if senator_list_data else None
    return render(
        request,
        "scorecard/county_detail.html",
        {
            "county": county,
            "senators": senator_list_data,
            "first_senator": first_senator,
        },
    )

