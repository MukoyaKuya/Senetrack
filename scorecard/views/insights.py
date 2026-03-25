import csv
import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.contrib.admin.views.decorators import staff_member_required

from scorecard.engine import perf_to_engine_data
from scorecard.models import Senator
from scorecard.services.analytics import get_senator_rows, normalize_frontier
from scorecard.services.insights_analytics import build_aggregate_stats, build_leaderboards, enrich_rows_with_computed_metrics
from scorecard.services.insights_charts import build_insights_charts
from scorecard.security import sanitize_county_slug, sanitize_filter_string

logger = logging.getLogger(__name__)

INSIGHTS_CACHE_TIMEOUT = 300  # 5 minutes


@cache_page(INSIGHTS_CACHE_TIMEOUT, key_prefix="frontier_v2")
def frontier_insights(request):
    """Frontier-focused analytics: compare performance across different frontiers (regions)."""
    all_rows = get_senator_rows()
    # Normalize to avoid duplicate options from inconsistent casing (e.g. "Western" vs "western")
    _seen = set()
    filter_frontiers = []
    for r in all_rows:
        f = r.get("frontier") or ""
        if f:
            key = normalize_frontier(f)
            if key not in _seen:
                _seen.add(key)
                filter_frontiers.append(key)
    filter_frontiers = sorted(filter_frontiers)

    # Apply frontier filter (case-insensitive); sanitize GET input
    filter_frontier_raw = sanitize_filter_string(request.GET.get("frontier") or "")
    filter_frontier = normalize_frontier(filter_frontier_raw) if filter_frontier_raw else ""
    rows = (
        [r for r in all_rows if normalize_frontier(r.get("frontier") or "") == filter_frontier]
        if filter_frontier
        else all_rows
    )

    # When filtered: show all senators from that frontier, sorted by score. Otherwise: best per frontier.
    if filter_frontier:
        senators_display = sorted(rows, key=lambda x: (x["overall_score"], x["name"]), reverse=True)
    else:
        # Use normalized frontier as key to handle inconsistent casing (e.g. "Western" vs "western")
        frontier_best = {}
        for r in all_rows:
            f = r.get("frontier") or ""
            if not f:
                continue
            key = normalize_frontier(f)
            if key not in frontier_best or r["overall_score"] > frontier_best[key]["overall_score"]:
                frontier_best[key] = r
        senators_display = sorted(
            frontier_best.values(),
            key=lambda x: (x["overall_score"], (x.get("frontier") or "").lower()),
            reverse=True,
        )

    # Frontier aggregates (from filtered rows)
    frontier_stats = {}
    for r in rows:
        f = r["frontier"]
        fs = frontier_stats.setdefault(f, {"frontier": f, "count": 0, "sum_score": 0})
        fs["count"] += 1
        fs["sum_score"] += r["overall_score"]
    for fs in frontier_stats.values():
        fs["avg_score"] = round(fs["sum_score"] / fs["count"], 1) if fs["count"] else 0
    frontier_chart = sorted(frontier_stats.values(), key=lambda x: x["avg_score"], reverse=True)

    # Frontier by metric (includes words for Hansard)
    frontier_by_metric = {}
    for r in rows:
        f = r["frontier"]
        if f not in frontier_by_metric:
            frontier_by_metric[f] = {"frontier": f, "scores": [], "attendance": [], "bills": [], "speeches": [], "words": []}
        frontier_by_metric[f]["scores"].append(r["overall_score"])
        frontier_by_metric[f]["attendance"].append(r["attendance_rate"])
        frontier_by_metric[f]["bills"].append(r["sponsored_bills"] + r["passed_bills"])
        frontier_by_metric[f]["speeches"].append(r["speeches"])
        frontier_by_metric[f]["words"].append(r.get("words_spoken", 0))
    for fb in frontier_by_metric.values():
        c = len(fb["scores"])
        fb["avg_score"] = round(sum(fb["scores"]) / c, 1) if c else 0
        fb["avg_attendance"] = round(sum(fb["attendance"]) / c, 1) if c else 0
        fb["avg_bills"] = round(sum(fb["bills"]) / c, 1) if c else 0
        fb["avg_speeches"] = round(sum(fb["speeches"]) / c, 0) if c else 0
        fb["avg_words"] = round(sum(fb["words"]) / c, 0) if c else 0
    frontier_by_metric = sorted(frontier_by_metric.values(), key=lambda x: x["avg_score"], reverse=True)

    total_active = len(rows)
    avg_overall = round(sum(r["overall_score"] for r in rows) / total_active, 1) if total_active else 0

    charts = {
        "frontier_scores": {
            "labels": [fs["frontier"].replace("_", " ").title() for fs in frontier_chart],
            "scores": [fs["avg_score"] for fs in frontier_chart],
        },
        "frontier_by_metric": {
            "labels": [f["frontier"].replace("_", " ").title() for f in frontier_by_metric],
            "avg_scores": [f["avg_score"] for f in frontier_by_metric],
            "avg_attendance": [f["avg_attendance"] for f in frontier_by_metric],
            "avg_bills": [f["avg_bills"] for f in frontier_by_metric],
            "avg_speeches": [f["avg_speeches"] for f in frontier_by_metric],
            "avg_words": [f["avg_words"] for f in frontier_by_metric],
        },
    }

    # charts_json removed to avoid double encoding when using json_script in template

    # Always load image URLs from DB so frontier cards show photos (avoid stale/empty cache)
    if senators_display:
        ids = [r["senator_id"] for r in senators_display]
        url_by_id = {}
        for sen in Senator.objects.filter(senator_id__in=ids):
            try:
                url = sen.display_image_url or ""
            except Exception:
                logger.warning("Could not resolve display_image_url for senator %s.", sen.senator_id)
                url = getattr(sen, "image_url", None) or ""
            url_by_id[sen.senator_id] = url
        senators_display = [
            {
                **r,
                "image_url": url_by_id.get(r["senator_id"], r.get("image_url") or ""),
                "display_image_url": url_by_id.get(r["senator_id"], r.get("image_url") or ""),
            }
            for r in senators_display
        ]

    return render(
        request,
        "scorecard/frontier.html",
        {
            "senators_display": senators_display,
            "filter_frontier": filter_frontier,
            "frontier_stats": frontier_chart,
            "frontier_by_metric": frontier_by_metric,
            "charts_data": charts,
            "filters": {"frontiers": filter_frontiers, "frontier": filter_frontier},
            "total_active": total_active,
            "avg_overall": avg_overall,
        },
    )


_geojson_cache = {}
_geojson_cache_time = 0
_GEOJSON_CACHE_TTL = 3600  # 1 hour


def _fetch_kenya_geojson():
    """Fetch Kenya counties GeoJSON (cached). Uses Django cache when available, else in-process. Tries URL first, then local static file."""
    import time
    import urllib.request
    from pathlib import Path

    cache_key = "scorecard:kenya_geojson"
    data = cache.get(cache_key)
    if data is not None:
        return data

    global _geojson_cache_time
    now = time.time()
    if _geojson_cache and (now - _geojson_cache_time) < _GEOJSON_CACHE_TTL:
        return _geojson_cache.get("data")
    url = getattr(settings, "KENYA_COUNTIES_GEOJSON_URL", "")
    # Try external URL first
    if url:
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read().decode())
                _geojson_cache["data"] = data
                _geojson_cache_time = now
                cache.set(cache_key, data, _GEOJSON_CACHE_TTL)
                return data
        except Exception:
            logger.warning("Failed to fetch Kenya GeoJSON from URL %s; trying local fallback.", url)
    # Fallback: local static file (bundled for reliability)
    local_path = Path(__file__).resolve().parent.parent / "static" / "scorecard" / "kenya_counties.geojson"
    if local_path.exists():
        try:
            with open(local_path, encoding="utf-8") as f:
                data = json.load(f)
                _geojson_cache["data"] = data
                _geojson_cache_time = now
                cache.set(cache_key, data, _GEOJSON_CACHE_TTL)
                return data
        except Exception:
            logger.exception("Failed to load local GeoJSON from %s.", local_path)
    return _geojson_cache.get("data")  # serve stale on error


def _build_frontier_map_data():
    """Build county maps and processed GeoJSON for frontier map. Returns dict for JSON or template context."""
    from scorecard.models import County
    from scorecard.services.county_frontier import (
        FRONTIER_COLORS,
        build_county_maps,
        resolve_region,
    )

    geojson_data = _fetch_kenya_geojson()
    counties = list(County.objects.all().values("name", "region", "slug"))
    county_region_map, county_slug_map = build_county_maps(counties)
    frontier_colors = FRONTIER_COLORS

    if geojson_data:
        kept = []
        for f in geojson_data.get("features", []):
            county = (f.get("properties", {}).get("COUNTY") or f.get("properties", {}).get("county") or f.get("properties", {}).get("name") or "").strip()
            region = resolve_region(county, county_region_map)
            if region is None:
                continue
            f.setdefault("properties", {})["frontier"] = region
            kept.append(f)
        geojson_data["features"] = kept

    return {
        "geojson_data": geojson_data,
        "county_region_map": county_region_map,
        "county_slug_map": county_slug_map,
        "frontier_colors": frontier_colors,
    }


def _get_frontier_map_metadata():
    """Lightweight metadata only (no GeoJSON). For fast page load with static GeoJSON."""
    from scorecard.models import County
    from scorecard.services.county_frontier import FRONTIER_COLORS, build_county_maps

    counties = list(County.objects.all().values("name", "region", "slug"))
    county_region_map, county_slug_map = build_county_maps(counties)
    return {"county_region_map": county_region_map, "county_slug_map": county_slug_map, "frontier_colors": FRONTIER_COLORS}


def frontier_map(request):
    """Map of Kenya showing frontiers. Metadata in page, GeoJSON loaded from static file."""
    from django.urls import reverse
    from django.templatetags.static import static

    metadata = _get_frontier_map_metadata()
    return render(
        request,
        "scorecard/frontier_map.html",
        {
            "geojson_static_url": static("scorecard/kenya_counties.geojson"),
            "map_metadata_json": json.dumps(metadata),
            "county_url_template": reverse("scorecard:county-detail", kwargs={"slug": "__SLUG__"}),
        },
    )


def frontier_map_data(request):
    """JSON endpoint: processed GeoJSON + maps for frontier map. Enables fast initial page load."""
    from django.http import JsonResponse

    data = _build_frontier_map_data()
    return JsonResponse(
        {
            "geojson_data": data["geojson_data"],
            "county_region_map": data["county_region_map"],
            "county_slug_map": data["county_slug_map"],
            "frontier_colors": data["frontier_colors"],
        }
    )


@cache_page(INSIGHTS_CACHE_TIMEOUT)
def data_insights(request):
    """Data insights dashboard with aggregate analytics."""
    from scorecard.models import County, Party

    all_rows = get_senator_rows()

    filter_parties = sorted(set(r["party"] for r in all_rows))
    filter_frontiers = sorted(set(r["frontier"] for r in all_rows))
    filter_counties = list(County.objects.values_list("slug", "name").order_by("name"))
    party_logos = {p.name.strip(): p.logo.url for p in Party.objects.filter(logo__isnull=False).only("name", "logo")}

    filter_party = sanitize_filter_string(request.GET.get("party") or "")
    filter_frontier = sanitize_filter_string(request.GET.get("frontier") or "").replace(" ", "_")
    raw_county = (request.GET.get("county") or "").strip().lower()
    filter_county = (sanitize_county_slug(raw_county) or "") if raw_county else ""

    rows = list(all_rows)
    if filter_party:
        rows = [r for r in rows if r["party"] == filter_party]
    if filter_frontier:
        rows = [r for r in rows if (r["frontier"] or "").replace(" ", "_") == filter_frontier]
    if filter_county:
        rows = [r for r in rows if (r.get("county_slug") or "").lower() == filter_county]

    if rows:
        senator_ids = [r["senator_id"] for r in rows]
        image_by_id = {}
        for sen in Senator.objects.filter(senator_id__in=senator_ids):
            try:
                url = sen.display_image_url or ""
            except Exception:
                logger.warning("Could not resolve display_image_url for senator %s.", sen.senator_id)
                url = getattr(sen, "image_url", None) or ""
            image_by_id[sen.senator_id] = url
        for r in rows:
            url = image_by_id.get(r["senator_id"], r.get("image_url") or "")
            r["image_url"] = url
            r["display_image_url"] = url

    enrich_rows_with_computed_metrics(rows)
    leaderboards = build_leaderboards(rows)
    agg = build_aggregate_stats(rows)

    sorted_rows = sorted(rows, key=lambda r: r["overall_score"], reverse=True)
    top10 = sorted_rows[:10]

    charts_input = {
        "rows": rows,
        "bins": agg["bins"],
        "frontier_chart": agg["frontier_chart"],
        "top_sponsored": leaderboards["sponsored_bills"],
        "committee_leadership_impact": agg["committee_leadership_impact"],
        "county_performance": agg["county_performance"],
        "grade_distribution": agg["grade_distribution"],
        "committee_role_stats": agg["committee_role_stats"],
        "party_performance": agg["party_performance"],
        "frontier_by_metric": agg["frontier_by_metric"],
        "nominated": agg["nominated"],
        "elected": agg["elected"],
        "nom_avg_score": agg["nominated_vs_elected"]["nom_avg_score"],
        "elec_avg_score": agg["nominated_vs_elected"]["elec_avg_score"],
        "nom_avg_att": agg["nominated_vs_elected"]["nom_avg_att"],
        "elec_avg_att": agg["nominated_vs_elected"]["elec_avg_att"],
        "grade_tier_stats": agg["grade_tier_stats"],
        "sorted_rows": sorted_rows,
    }
    charts = build_insights_charts(charts_input)

    active_senators = []
    if filter_party or filter_frontier or filter_county:
        active_senators = sorted(
            [{"name": r["name"], "senator_id": r["senator_id"]} for r in rows],
            key=lambda x: x["name"],
        )

    filtered_senators = sorted(rows, key=lambda r: (r["overall_score"], r["name"]), reverse=True)

    return render(
        request,
        "scorecard/insights.html",
        {
            "metrics": agg["metrics"],
            "top10": top10,
            "leaderboards": leaderboards,
            "charts_json": json.dumps(charts),
            "party_performance": agg["party_performance"],
            "frontier_by_metric": agg["frontier_by_metric"],
            "committee_role_stats": agg["committee_role_stats"],
            "grade_distribution": agg["grade_distribution"],
            "committee_leadership_impact": agg["committee_leadership_impact"],
            "county_performance": agg["county_performance"],
            "nominated_vs_elected": agg["nominated_vs_elected"],
            "top_improving": agg["top_improving"],
            "top_declining": agg["top_declining"],
            "filters": {
                "parties": filter_parties,
                "frontiers": filter_frontiers,
                "counties": filter_counties,
                "party": filter_party,
                "frontier": filter_frontier,
                "county": filter_county,
                "party_logos": party_logos,
            },
            "deceased_excluded": True,
            "best_per_frontier": agg["best_per_frontier"],
            "grade_tier_stats": agg["grade_tier_stats"],
            "active_senators": active_senators,
            "filtered_senators": filtered_senators,
        },
    )


_CSV_FIELDS = [
    ("name", "Senator"),
    ("county", "County"),
    ("party", "Party"),
    ("frontier", "Region"),
    ("overall_score", "Overall Score"),
    ("grade", "Grade"),
    ("attendance_rate", "Attendance Rate (%)"),
    ("sessions_attended", "Sessions Attended"),
    ("speeches", "Speeches"),
    ("words_spoken", "Words Spoken"),
    ("motions_sponsored", "Motions Sponsored"),
    ("sponsored_bills", "Bills Sponsored"),
    ("passed_bills", "Bills Passed"),
    ("amendments", "Amendments"),
    ("committee_role", "Committee Role"),
    ("committee_attendance", "Committee Attendance"),
    ("vote_rate", "Vote Rate (%)"),
    ("county_representation", "County Rep. Score"),
    ("oversight_actions", "Oversight Actions"),
]


@staff_member_required
def export_insights_csv(request):
    """Download all senator performance data as a CSV file."""
    rows = get_senator_rows()
    rows = sorted(rows, key=lambda r: r.get("overall_score", 0), reverse=True)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="senetrack_performance_2025.csv"'

    writer = csv.writer(response)
    writer.writerow([label for _, label in _CSV_FIELDS])
    for r in rows:
        writer.writerow([r.get(key, "") for key, _ in _CSV_FIELDS])

    return response

