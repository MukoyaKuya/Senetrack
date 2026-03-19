import csv
import json

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page

from scorecard.engine import perf_to_engine_data
from scorecard.models import Senator
from scorecard.services.analytics import get_senator_rows, normalize_frontier
from scorecard.services.insights_charts import build_insights_charts
from scorecard.security import sanitize_county_slug, sanitize_filter_string

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

    charts_json = json.dumps(charts).replace("</", "<\\/")

    # Always load image URLs from DB so frontier cards show photos (avoid stale/empty cache)
    if senators_display:
        ids = [r["senator_id"] for r in senators_display]
        url_by_id = {}
        for sen in Senator.objects.filter(senator_id__in=ids):
            try:
                # Use the Senator.display_image_url helper for consistent media/Cloudinary handling
                url = sen.display_image_url or ""
            except Exception:
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
            "charts_json": charts_json,
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
            pass
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
            pass
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
            "county_url_template": reverse("county-detail", kwargs={"slug": "__SLUG__"}),
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
    rows = get_senator_rows()

    # Filter options from full dataset (before applying filters)
    filter_parties = sorted(set(r["party"] for r in rows))
    filter_frontiers = sorted(set(r["frontier"] for r in rows))
    from scorecard.models import County, Party
    filter_counties = list(County.objects.values_list("slug", "name").order_by("name"))
    party_logos = {p.name.strip(): p.logo.url for p in Party.objects.filter(logo__isnull=False).only("name", "logo")}

    # Apply filters from GET params (sanitized to prevent injection/abuse)
    filter_party = sanitize_filter_string(request.GET.get("party") or "")
    filter_frontier = sanitize_filter_string(request.GET.get("frontier") or "").replace(" ", "_")
    raw_county = (request.GET.get("county") or "").strip().lower()
    filter_county = (sanitize_county_slug(raw_county) or "") if raw_county else ""
    if filter_party:
        rows = [r for r in rows if r["party"] == filter_party]
    if filter_frontier:
        rows = [r for r in rows if (r["frontier"] or "").replace(" ", "_") == filter_frontier]
    if filter_county:
        rows = [r for r in rows if (r.get("county_slug") or "").lower() == filter_county]

    # Enrich filtered rows with live image URLs from the Senator model so cards can render photos.
    if rows:
        senator_ids = [r["senator_id"] for r in rows]
        image_by_id = {}
        for sen in Senator.objects.filter(senator_id__in=senator_ids):
            try:
                url = sen.display_image_url or ""
            except Exception:
                url = getattr(sen, "image_url", None) or ""
            image_by_id[sen.senator_id] = url
        for r in rows:
            url = image_by_id.get(r["senator_id"], r.get("image_url") or "")
            r["image_url"] = url
            r["display_image_url"] = url

    # Best performed senator per frontier (top by overall_score)
    frontier_best = {}
    for r in rows:
        f = r["frontier"]
        if f not in frontier_best or r["overall_score"] > frontier_best[f]["overall_score"]:
            frontier_best[f] = r
    best_per_frontier = sorted(
        frontier_best.values(),
        key=lambda x: (x["overall_score"], x["frontier"]),
        reverse=True,
    )

    total_active = len(rows)
    avg_overall = round(sum(r["overall_score"] for r in rows) / total_active, 1) if total_active else 0
    avg_attendance = round(sum(r["attendance_rate"] for r in rows) / total_active, 1) if total_active else 0
    total_bills = sum(r["sponsored_bills"] for r in rows)
    total_passed = sum(r["passed_bills"] for r in rows)
    pass_rate = round((total_passed / total_bills) * 100, 1) if total_bills else 0
    total_words = sum(r["words_spoken"] for r in rows)
    total_speeches = sum(r["speeches"] for r in rows)
    total_motions = sum(r["motions_sponsored"] for r in rows)

    # Frontier aggregates
    frontier_stats = {}
    for r in rows:
        f = r["frontier"]
        fs = frontier_stats.setdefault(f, {"frontier": f, "count": 0, "sum_score": 0})
        fs["count"] += 1
        fs["sum_score"] += r["overall_score"]
    for fs in frontier_stats.values():
        fs["avg_score"] = round(fs["sum_score"] / fs["count"], 1) if fs["count"] else 0
    frontier_chart = sorted(frontier_stats.values(), key=lambda x: x["avg_score"], reverse=True)

    # Score distribution (bins of 10)
    bins = [0] * 10
    for r in rows:
        score = max(0, min(99, int(r["overall_score"])))
        idx = score // 10
        bins[idx] += 1

    sorted_rows = sorted(rows, key=lambda r: r["overall_score"], reverse=True)
    top10 = sorted_rows[:10]
    bottom10 = list(reversed(sorted_rows[-10:])) if sorted_rows else []

    # Leaderboards: highest by specific metrics (Hansard + legacy)
    top_attendance = sorted(rows, key=lambda r: r["attendance_rate"], reverse=True)[:10]
    top_sponsored = sorted(rows, key=lambda r: r["sponsored_bills"], reverse=True)[:10]
    top_passed = sorted(rows, key=lambda r: r["passed_bills"], reverse=True)[:10]
    top_speeches = sorted(rows, key=lambda r: r["speeches"], reverse=True)[:10]
    top_words = sorted(rows, key=lambda r: r["words_spoken"], reverse=True)[:10]
    top_motions = sorted(rows, key=lambda r: r["motions_sponsored"], reverse=True)[:10]
    top_sessions = sorted(rows, key=lambda r: r["sessions_attended"], reverse=True)[:10]
    top_amendments = sorted(rows, key=lambda r: r["amendments"], reverse=True)[:10]
    top_committee = sorted(rows, key=lambda r: r["committee_attendance"], reverse=True)[:10]
    top_vote_rate = sorted(rows, key=lambda r: r["vote_rate"], reverse=True)[:10]
    top_oversight = sorted(rows, key=lambda r: r["oversight_actions"], reverse=True)[:10]
    top_statements_2025 = sorted(
        [r for r in rows if r.get("statements_2025", 0) > 0],
        key=lambda r: r["statements_2025"],
        reverse=True,
    )[:10]

    # Best pass rate (min 2 sponsored to qualify)
    pass_rate_rows = [r for r in rows if r["sponsored_bills"] >= 2]
    top_pass_rate = sorted(pass_rate_rows, key=lambda r: (r["passed_bills"] / r["sponsored_bills"], r["passed_bills"]), reverse=True)[:10]

    # County representation leaderboard
    top_county_rep = sorted(rows, key=lambda r: r["county_representation"], reverse=True)[:10]

    # Most votes missed (worst vote participation)
    most_votes_missed = sorted(rows, key=lambda r: r["votes_missed"], reverse=True)[:10]

    # Legislative quality vs quantity: high quality = high pass rate + at least 1 sponsored; high quantity = many sponsored
    quality_rows = [r for r in rows if r["sponsored_bills"] >= 1]
    for r in quality_rows:
        r["pass_rate_pct"] = round((r["passed_bills"] / r["sponsored_bills"]) * 100, 1) if r["sponsored_bills"] else 0
    high_quality = sorted(quality_rows, key=lambda r: (r["pass_rate_pct"], r["passed_bills"]), reverse=True)[:10]
    high_quantity = sorted(rows, key=lambda r: (r["sponsored_bills"], r["passed_bills"]), reverse=True)[:10]

    # Committee leadership impact: Chairs/Vice Chairs vs Members avg score
    leadership_roles = {"Chair", "Vice Chair", "Majority Leader", "Deputy Minority Whip", "Ranking Member"}
    leaders = [r for r in rows if r["committee_role"] in leadership_roles]
    members = [r for r in rows if r["committee_role"] not in leadership_roles]
    committee_leadership_impact = {
        "leaders_avg": round(sum(r["overall_score"] for r in leaders) / len(leaders), 1) if leaders else 0,
        "leaders_count": len(leaders),
        "members_avg": round(sum(r["overall_score"] for r in members) / len(members), 1) if members else 0,
        "members_count": len(members),
    }

    # County-level performance (avg score, attendance, bills per county)
    county_perf = {}
    for r in rows:
        key = r.get("county_slug") or r["county"] or "other"
        if key not in county_perf:
            county_perf[key] = {"county": r["county"] or key, "slug": key, "scores": [], "attendance": [], "bills": []}
        county_perf[key]["scores"].append(r["overall_score"])
        county_perf[key]["attendance"].append(r["attendance_rate"])
        county_perf[key]["bills"].append(r["sponsored_bills"] + r["passed_bills"])
    for cp in county_perf.values():
        c = len(cp["scores"])
        cp["avg_score"] = round(sum(cp["scores"]) / c, 1) if c else 0
        cp["avg_attendance"] = round(sum(cp["attendance"]) / c, 1) if c else 0
        cp["avg_bills"] = round(sum(cp["bills"]) / c, 1) if c else 0
        cp["senator_count"] = c
    county_performance = sorted(county_perf.values(), key=lambda x: x["avg_score"], reverse=True)[:20]

    # Efficiency: bills passed per speech (min 10 speeches to qualify)
    eff_rows = [r for r in rows if r["speeches"] >= 10]
    for r in eff_rows:
        r["efficiency"] = round((r["passed_bills"] / r["speeches"]) * 100, 2) if r["speeches"] else 0
    top_efficiency = sorted(eff_rows, key=lambda r: r["efficiency"], reverse=True)[:10]

    # All-rounders: top 25% in attendance, speeches, votes, legislative (Hansard-aware)
    n = len(rows)
    if n >= 4:
        q = max(1, n // 4)
        att_thresh = sorted([r["attendance_rate"] for r in rows], reverse=True)[q - 1]
        sp_thresh = sorted([r["speeches"] for r in rows], reverse=True)[q - 1]
        vote_thresh = sorted([r["vote_rate"] for r in rows], reverse=True)[q - 1]
        leg_thresh = sorted([r["sponsored_bills"] + r["passed_bills"] * 2 for r in rows], reverse=True)[q - 1]
        all_rounders = [
            r for r in rows
            if r["attendance_rate"] >= att_thresh
            and r["speeches"] >= sp_thresh
            and r["vote_rate"] >= vote_thresh
            and (r["sponsored_bills"] + r["passed_bills"] * 2) >= leg_thresh
        ]
        all_rounders = sorted(all_rounders, key=lambda r: r["overall_score"], reverse=True)[:10]
    else:
        all_rounders = []

    # Hansard-specific: words per speech (verbosity) - min 10 speeches
    verbosity_rows = [r for r in rows if r["speeches"] >= 10]
    for r in verbosity_rows:
        r["words_per_speech"] = round(r["words_spoken"] / r["speeches"], 1) if r["speeches"] else 0
    top_verbosity = sorted(verbosity_rows, key=lambda r: r["words_per_speech"], reverse=True)[:10]

    # --- NEW ANALYTICS: Enrich all rows with computed metrics ---
    for r in rows:
        r["speeches_per_session"] = round(r["speeches"] / r["sessions_attended"], 1) if r["sessions_attended"] else 0
        r["bills_per_session"] = round(r["sponsored_bills"] / r["sessions_attended"], 2) if r["sessions_attended"] else 0
        r["bills_per_speech"] = round(r["sponsored_bills"] / r["speeches"], 2) if r["speeches"] else 0
        r["motions_per_speech"] = round(r["motions_sponsored"] / r["speeches"], 2) if r["speeches"] else 0
        r["words_per_speech"] = round(r["words_spoken"] / r["speeches"], 1) if r["speeches"] else 0
        # Structural vs debate ratio (55 vs 45 pts max)
        s_sc, d_sc = r.get("structural_score", 0) or 0, r.get("debate_score", 0) or 0
        r["structural_debate_ratio"] = round(s_sc / d_sc, 2) if d_sc else (s_sc if s_sc else 0)
        # Composite indices (0-100 scale, normalized)
        r["floor_leader_index"] = round(min(100, (r["words_spoken"] / 1500 + r["speeches"] / 35 + r["motions_sponsored"] * 2)), 1)
        r["legislative_workhorse_index"] = round(min(100, (r["sponsored_bills"] * 5 + r["vote_rate"] * 0.3 + r["sessions_attended"] / 1.2)), 1)
        r["balanced_contributor"] = round(100 - abs(s_sc - d_sc), 1) if (s_sc or d_sc) else 0

    # 1. PARTICIPATION BALANCE
    structural_heavy = sorted([r for r in rows if r["structural_score"] > r["debate_score"] + 5], key=lambda r: r["structural_score"], reverse=True)[:10]
    debate_heavy = sorted([r for r in rows if r["debate_score"] > r["structural_score"] + 5], key=lambda r: r["debate_score"], reverse=True)[:10]
    balanced = sorted([r for r in rows if abs(r["structural_score"] - r["debate_score"]) <= 5], key=lambda r: r["overall_score"], reverse=True)[:10]

    # 2. FLOOR PRESENCE
    sp_per_sess = [r for r in rows if r["sessions_attended"] >= 10]
    for r in sp_per_sess:
        r["speeches_per_session"] = round(r["speeches"] / r["sessions_attended"], 1)
    top_speeches_per_session = sorted(sp_per_sess, key=lambda r: r["speeches_per_session"], reverse=True)[:10]
    silent_attenders = sorted([r for r in rows if r["sessions_attended"] >= 20 and r["speeches"] < 100], key=lambda r: r["sessions_attended"], reverse=True)[:10]

    # 3. SPEAKING STYLE: Punchy (many speeches, low words/speech) vs Verbose
    punchy = sorted([r for r in verbosity_rows if r["words_per_speech"] < 60], key=lambda r: r["speeches"], reverse=True)[:10]

    # 4. LEGISLATIVE EFFICIENCY
    bills_per_sess = [r for r in rows if r["sessions_attended"] >= 5 and r["sponsored_bills"] > 0]
    for r in bills_per_sess:
        r["bills_per_session"] = round(r["sponsored_bills"] / r["sessions_attended"], 2)
    top_bills_per_session = sorted(bills_per_sess, key=lambda r: r["bills_per_session"], reverse=True)[:10]
    bills_per_sp = [r for r in rows if r["speeches"] >= 20 and r["sponsored_bills"] > 0]
    for r in bills_per_sp:
        r["bills_per_speech"] = round(r["sponsored_bills"] / r["speeches"], 3)
    top_bills_per_speech = sorted(bills_per_sp, key=lambda r: r["bills_per_speech"], reverse=True)[:10]

    # 5. OUTLIERS
    high_bills_low_debate = sorted([r for r in rows if r["sponsored_bills"] >= 5 and r["debate_score"] < 30], key=lambda r: r["sponsored_bills"], reverse=True)[:10]
    high_motions_low_speeches = sorted([r for r in rows if r["motions_sponsored"] >= 5 and r["speeches"] < 200], key=lambda r: r["motions_sponsored"], reverse=True)[:10]
    high_words_low_score = sorted([r for r in rows if r["words_spoken"] >= 50000 and r["overall_score"] < 50], key=lambda r: r["words_spoken"], reverse=True)[:10]

    # 6. COMPOSITE INDICES leaderboards
    top_floor_leader = sorted(rows, key=lambda r: r["floor_leader_index"], reverse=True)[:10]
    top_legislative_workhorse = sorted(rows, key=lambda r: r["legislative_workhorse_index"], reverse=True)[:10]
    top_balanced = sorted(rows, key=lambda r: r["balanced_contributor"], reverse=True)[:10]

    # 7. COHORT: By grade tier (avg words, speeches, motions per grade)
    grade_tier_stats = {}
    for r in rows:
        g = r["grade"]
        if g not in grade_tier_stats:
            grade_tier_stats[g] = {"grade": g, "count": 0, "words": [], "speeches": [], "motions": [], "structural": [], "debate": []}
        grade_tier_stats[g]["count"] += 1
        grade_tier_stats[g]["words"].append(r["words_spoken"])
        grade_tier_stats[g]["speeches"].append(r["speeches"])
        grade_tier_stats[g]["motions"].append(r["motions_sponsored"])
        grade_tier_stats[g]["structural"].append(r["structural_score"])
        grade_tier_stats[g]["debate"].append(r["debate_score"])
    for gs in grade_tier_stats.values():
        c = gs["count"]
        gs["avg_words"] = round(sum(gs["words"]) / c, 0) if c else 0
        gs["avg_speeches"] = round(sum(gs["speeches"]) / c, 0) if c else 0
        gs["avg_motions"] = round(sum(gs["motions"]) / c, 1) if c else 0
        gs["avg_structural"] = round(sum(gs["structural"]) / c, 1) if c else 0
        gs["avg_debate"] = round(sum(gs["debate"]) / c, 1) if c else 0
    GRADE_ORDER = {"A": 0, "A-": 1, "B+": 2, "B": 3, "B-": 4, "C+": 5, "C": 6, "C-": 7, "D+": 8, "D": 9, "D-": 10, "E": 11, "NEW": 12, "—": 13}
    grade_tier_stats = sorted(grade_tier_stats.values(), key=lambda x: GRADE_ORDER.get(x["grade"], 99))

    # 8. PEER BENCHMARKS: Percentile ranks
    def _percentile_rank(val, arr):
        if not arr:
            return 0
        arr_sorted = sorted(arr)
        below = sum(1 for x in arr_sorted if x < val)
        return round((below / len(arr_sorted)) * 100, 0)

    words_arr = [r["words_spoken"] for r in rows]
    speeches_arr = [r["speeches"] for r in rows]
    for r in rows:
        r["words_percentile"] = _percentile_rank(r["words_spoken"], words_arr)
        r["speeches_percentile"] = _percentile_rank(r["speeches"], speeches_arr)
    top_words_percentile = sorted(rows, key=lambda r: r["words_percentile"], reverse=True)[:10]

    # 9. VOTING: High vote rate + low debate (or reverse)
    vote_heavy_low_debate = sorted([r for r in rows if r["vote_rate"] >= 90 and r["debate_score"] < 35], key=lambda r: r["vote_rate"], reverse=True)[:10]
    debate_heavy_low_vote = sorted([r for r in rows if r["debate_score"] >= 38 and r["vote_rate"] < 80], key=lambda r: r["debate_score"], reverse=True)[:10]

    # Gap analysis: high attendance + low legislative output
    high_att = sorted(rows, key=lambda r: r["attendance_rate"], reverse=True)[:n // 2] if n else []
    leg_output = lambda r: r["sponsored_bills"] + r["passed_bills"] + r["amendments"]
    gap_high_att_low_leg = sorted(
        [r for r in high_att if leg_output(r) <= 2],
        key=lambda r: r["attendance_rate"],
        reverse=True,
    )[:10]

    # Gap: low attendance + high legislative output
    high_leg = sorted(rows, key=leg_output, reverse=True)[:n // 2] if n else []
    gap_low_att_high_leg = sorted(
        [r for r in high_leg if r["attendance_rate"] < 70],
        key=leg_output,
        reverse=True,
    )[:10]

    # Nominated vs elected
    nominated = [r for r in rows if r["is_nominated"]]
    elected = [r for r in rows if not r["is_nominated"]]
    nom_avg_score = round(sum(r["overall_score"] for r in nominated) / len(nominated), 1) if nominated else 0
    elec_avg_score = round(sum(r["overall_score"] for r in elected) / len(elected), 1) if elected else 0
    nom_avg_att = round(sum(r["attendance_rate"] for r in nominated) / len(nominated), 1) if nominated else 0
    elec_avg_att = round(sum(r["attendance_rate"] for r in elected) / len(elected), 1) if elected else 0

    # Frontier by metric (avg attendance, bills, speeches, words per senator)
    frontier_by_metric = {}
    for r in rows:
        f = r["frontier"]
        if f not in frontier_by_metric:
            frontier_by_metric[f] = {"frontier": f, "scores": [], "attendance": [], "bills": [], "speeches": [], "words": []}
        frontier_by_metric[f]["scores"].append(r["overall_score"])
        frontier_by_metric[f]["attendance"].append(r["attendance_rate"])
        frontier_by_metric[f]["bills"].append(r["sponsored_bills"] + r["passed_bills"])
        frontier_by_metric[f]["speeches"].append(r["speeches"])
        frontier_by_metric[f]["words"].append(r["words_spoken"])
    for fb in frontier_by_metric.values():
        c = len(fb["scores"])
        fb["avg_score"] = round(sum(fb["scores"]) / c, 1) if c else 0
        fb["avg_attendance"] = round(sum(fb["attendance"]) / c, 1) if c else 0
        fb["avg_bills"] = round(sum(fb["bills"]) / c, 1) if c else 0
        fb["avg_speeches"] = round(sum(fb["speeches"]) / c, 0) if c else 0
        fb["avg_words"] = round(sum(fb["words"]) / c, 0) if c else 0
    frontier_by_metric = sorted(frontier_by_metric.values(), key=lambda x: x["avg_score"], reverse=True)

    # Committee role distribution
    role_counts = {}
    role_scores = {}
    for r in rows:
        role = r["committee_role"]
        role_counts[role] = role_counts.get(role, 0) + 1
        if role not in role_scores:
            role_scores[role] = []
        role_scores[role].append(r["overall_score"])
    committee_role_stats = [
        {
            "role": role,
            "count": role_counts[role],
            "avg_score": round(sum(role_scores[role]) / len(role_scores[role]), 1) if role_scores[role] else 0,
        }
        for role in sorted(role_counts.keys(), key=lambda r: role_counts[r], reverse=True)
    ]

    # Grade distribution (order: A, A-, B+, B, B-, C+, C, C-, D+, D, D-, E)
    GRADE_ORDER = {"A": 0, "A-": 1, "B+": 2, "B": 3, "B-": 4, "C+": 5, "C": 6, "C-": 7, "D+": 8, "D": 9, "D-": 10, "E": 11, "NEW": 12, "—": 13}
    grade_counts = {}
    for r in rows:
        g = r["grade"]
        grade_counts[g] = grade_counts.get(g, 0) + 1
    grade_distribution = sorted(
        [{"grade": g, "count": c} for g, c in grade_counts.items()],
        key=lambda x: (GRADE_ORDER.get(x["grade"], 99), x["grade"]),
    )

    # Party performance
    party_stats = {}
    for r in rows:
        p = r["party"]
        if p not in party_stats:
            party_stats[p] = {"party": p, "count": 0, "scores": []}
        party_stats[p]["count"] += 1
        party_stats[p]["scores"].append(r["overall_score"])
    for ps in party_stats.values():
        ps["avg_score"] = round(sum(ps["scores"]) / len(ps["scores"]), 1) if ps["scores"] else 0
    party_performance = sorted(
        party_stats.values(),
        key=lambda x: (x["avg_score"], x["count"]),
        reverse=True,
    )[:15]

    # Trend: improving vs declining (from trend_data)
    improving, declining = [], []
    for r in rows:
        td = r.get("trend_data") or []
        if not isinstance(td, list) or len(td) < 2:
            continue
        scores = []
        for point in td:
            if isinstance(point, dict) and "score" in point:
                scores.append(float(point["score"]))
            elif isinstance(point, (int, float)):
                scores.append(float(point))
        if len(scores) >= 2:
            r_copy = dict(r)
            r_copy["trend_direction"] = "improving" if scores[-1] > scores[0] else "declining"
            r_copy["trend_change"] = round(scores[-1] - scores[0], 1)
            if scores[-1] > scores[0]:
                improving.append(r_copy)
            else:
                declining.append(r_copy)
    top_improving = sorted(improving, key=lambda r: r["trend_change"], reverse=True)[:10]
    top_declining = sorted(declining, key=lambda r: r["trend_change"])[:10]

    leaderboards = {
        "attendance": top_attendance,
        "sponsored_bills": top_sponsored,
        "passed_bills": top_passed,
        "speeches": top_speeches,
        "words_spoken": top_words,
        "motions_sponsored": top_motions,
        "sessions_attended": top_sessions,
        "verbosity": top_verbosity,
        "speeches_per_session": top_speeches_per_session,
        "silent_attenders": silent_attenders,
        "punchy_speakers": punchy,
        "bills_per_session": top_bills_per_session,
        "bills_per_speech": top_bills_per_speech,
        "structural_heavy": structural_heavy,
        "debate_heavy": debate_heavy,
        "balanced_contributors": balanced,
        "floor_leader": top_floor_leader,
        "legislative_workhorse": top_legislative_workhorse,
        "balanced_index": top_balanced,
        "high_bills_low_debate": high_bills_low_debate,
        "high_words_low_score": high_words_low_score,
        "high_motions_low_speeches": high_motions_low_speeches,
        "vote_heavy_low_debate": vote_heavy_low_debate,
        "debate_heavy_low_vote": debate_heavy_low_vote,
        "words_percentile": top_words_percentile,
        "amendments": top_amendments,
        "committee_attendance": top_committee,
        "vote_rate": top_vote_rate,
        "oversight_actions": top_oversight,
        "statements_2025": top_statements_2025,
        "pass_rate": top_pass_rate,
        "county_representation": top_county_rep,
        "efficiency": top_efficiency,
        "all_rounders": all_rounders,
        "gap_high_att_low_leg": gap_high_att_low_leg,
        "gap_low_att_high_leg": gap_low_att_high_leg,
        "most_votes_missed": most_votes_missed,
        "high_quality_legislative": high_quality,
        "high_quantity_legislative": high_quantity,
    }

    aggregates = {
        "rows": rows,
        "bins": bins,
        "frontier_chart": frontier_chart,
        "top_sponsored": top_sponsored,
        "committee_leadership_impact": committee_leadership_impact,
        "county_performance": county_performance,
        "grade_distribution": grade_distribution,
        "committee_role_stats": committee_role_stats,
        "party_performance": party_performance,
        "frontier_by_metric": frontier_by_metric,
        "nominated": nominated,
        "elected": elected,
        "nom_avg_score": nom_avg_score,
        "elec_avg_score": elec_avg_score,
        "nom_avg_att": nom_avg_att,
        "elec_avg_att": elec_avg_att,
        "grade_tier_stats": grade_tier_stats,
        "sorted_rows": sorted_rows,
    }
    charts = build_insights_charts(aggregates)

    metrics = {
        "total_active": total_active,
        "avg_overall": avg_overall,
        "avg_attendance": avg_attendance,
        "total_bills": total_bills,
        "total_passed": total_passed,
        "pass_rate": pass_rate,
        "total_words": total_words,
        "total_speeches": total_speeches,
        "total_motions": total_motions,
    }

    # When filters are applied, list senator names for the Active Senators card
    active_senators = []
    if filter_party or filter_frontier or filter_county:
        active_senators = sorted(
            [{"name": r["name"], "senator_id": r["senator_id"]} for r in rows],
            key=lambda x: x["name"],
        )

    # Full filtered list for senator cards (sorted by score desc, then name)
    filtered_senators = sorted(
        rows,
        key=lambda r: (r["overall_score"], r["name"]),
        reverse=True,
    )

    return render(
        request,
        "scorecard/insights.html",
        {
            "metrics": metrics,
            "top10": top10,
            "leaderboards": leaderboards,
            "charts_json": json.dumps(charts),
            "party_performance": party_performance,
            "frontier_by_metric": frontier_by_metric,
            "committee_role_stats": committee_role_stats,
            "grade_distribution": grade_distribution,
            "committee_leadership_impact": committee_leadership_impact,
            "county_performance": county_performance,
            "nominated_vs_elected": {
                "nominated_count": len(nominated),
                "elected_count": len(elected),
                "nom_avg_score": nom_avg_score,
                "elec_avg_score": elec_avg_score,
                "nom_avg_att": nom_avg_att,
                "elec_avg_att": elec_avg_att,
            },
            "top_improving": top_improving,
            "top_declining": top_declining,
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
            "best_per_frontier": best_per_frontier,
            "grade_tier_stats": grade_tier_stats,
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

