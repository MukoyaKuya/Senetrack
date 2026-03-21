from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_page

from scorecard.models import County, Party, Senator
from scorecard.security import sanitize_county_slug


@cache_page(60)
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

    party_logo_entries = [
        (p.name.strip(), p.display_logo_url)
        for p in Party.objects.filter(logo__isnull=False).exclude(logo="").only("name", "logo")
    ]
    party_logos = dict(party_logo_entries)

    def _party_logo(party_name):
        if not party_name:
            return None
        key = party_name.strip()
        # Exact match first
        if key in party_logos:
            return party_logos[key]
        # Case-insensitive fallback
        key_lower = key.lower()
        for name, url in party_logo_entries:
            if name.lower() == key_lower:
                return url
        # Partial match: either name contains the other (handles abbreviations / extra words)
        for name, url in party_logo_entries:
            if name.lower() in key_lower or key_lower in name.lower():
                return url
        return None

    matched = list(county.senators.select_related("perf").order_by("name"))
    senator_list_data = []
    for s in matched:
        p = getattr(s, "perf", None)
        grade = (p.grade or "—") if p else "—"
        overall_score = (p.overall_score or 0) if p else 0
        senator_list_data.append(
            {
                "senator_id": s.senator_id,
                "name": s.name,
                "county": county.name,
                "party": s.party,
                "party_logo_url": _party_logo(s.party),
                "image_url": s.display_image_url,
                "display_image_url": s.display_image_url,
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
            "governor_party_logo": _party_logo(county.governor_party),
            "women_rep_party_logo": _party_logo(county.women_rep_party),
        },
    )

