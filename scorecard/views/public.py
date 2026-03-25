from pathlib import Path

from django.conf import settings
from django.db.models import Avg, Count, F, Q, Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from scorecard.models import ParliamentaryPerformance, Senator, Party
from scorecard.services.senators import get_frontier
from scorecard.forms import ContactMessageForm
from scorecard import spam_guard


ACTIVE_DEBATES_DEFAULT = 12
CACHE_PAGE_SENATORS = 60
CACHE_PAGE_HOME = 60


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

    top_performers = []
    top_perf_qs = (
        ParliamentaryPerformance.objects
        .select_related("senator__county_fk")
        .filter(senator__is_deceased=False, senator__is_still_computing=False, overall_score__gt=0)
        .order_by("-overall_score")[:5]
    )
    for perf in top_perf_qs:
        s = perf.senator
        county_fk = getattr(s, "county_fk", None)
        top_performers.append({
            "senator_id": s.senator_id,
            "name": s.name,
            "county": getattr(county_fk, "name", "—"),
            "party": s.party or "",
            "grade": perf.grade or "—",
            "overall_score": perf.overall_score or 0,
            "display_image_url": s.display_image_url,
        })

    return render(
        request,
        "scorecard/home.html",
        {
            "total_senators": total_senators,
            "total_bills": total_bills,
            "avg_attendance": avg_attendance,
            "active_debates": active_debates,
            "top_performers": top_performers,
        },
    )


@cache_page(CACHE_PAGE_SENATORS)
def senator_list(request):
    """List of all senators with pagination."""
    senators_qs = Senator.objects.select_related("perf", "county_fk").order_by("name")
    party_logos = {p.name.strip(): p.display_logo_url for p in Party.objects.filter(logo__isnull=False).only("name", "logo")}
    PLACEHOLDER_NAME = "{{ senator.name }}"
    senator_list_data = []
    for s in senators_qs:
        name = s.senator_id.replace("-", " ").title() if s.name == PLACEHOLDER_NAME else s.name
        county = getattr(getattr(s, "county_fk", None), "name", "—")
        # Prefer the model's display_image_url helper so local media/Cloudinary work consistently
        image_url = s.display_image_url
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
                "display_image_url": image_url,
                "overall_score": overall_score,
                "grade": grade,
                "is_deceased": getattr(s, "is_deceased", False),
                "is_still_computing": getattr(s, "is_still_computing", False) or (overall_score > 0 and overall_score <= 50),
                "is_no_longer_serving": getattr(s, "is_no_longer_serving", False),
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


def _get_client_ip(request) -> str | None:
    """Return the real client IP, respecting X-Forwarded-For in production."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@require_http_methods(["GET", "POST"])
def about(request):
    """About page with performance engine documentation and contact form."""
    submitted = request.GET.get("submitted") == "1"

    if request.method == "POST":
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            ip = _get_client_ip(request)
            email = form.cleaned_data.get("email", "")
            body  = form.cleaned_data.get("body", "")

            # Rate-limit and duplicate checks happen post-validation so we
            # have clean, normalised values to work with.
            try:
                spam_guard.check_rate_limit(ip, email)
                spam_guard.check_duplicate(ip, body)
            except spam_guard.SpamError as exc:
                reason = str(exc)
                if "duplicate" in reason:
                    # Show success to avoid timing-based probing
                    return redirect(request.path + "?submitted=1#feedback")
                if "rate_limit_hour" in reason:
                    form.add_error(None, (
                        "You have submitted too many messages recently. "
                        "Please wait an hour before trying again."
                    ))
                elif "rate_limit_day" in reason:
                    form.add_error(None, (
                        "You have reached the daily submission limit. "
                        "Please try again tomorrow."
                    ))
                elif "rate_limit_email" in reason:
                    form.add_error(None, (
                        "This email address has already submitted feedback today. "
                        "Please use a different address or try again tomorrow."
                    ))
            else:
                msg = form.save(commit=False)
                msg.ip_address = ip
                msg.save()
                return redirect(request.path + "?submitted=1#feedback")
    else:
        form = ContactMessageForm()

    return render(request, "scorecard/about.html", {
        "contact_form": form,
        "submitted": submitted,
    })


@cache_page(300)
def key_findings(request):
    """Key Findings page with curated data insights derived from live DB."""
    active_qs = ParliamentaryPerformance.objects.select_related(
        "senator__county_fk"
    ).filter(senator__is_deceased=False)

    scored_qs = active_qs.filter(senator__is_still_computing=False, overall_score__gt=0)
    all_scores = list(scored_qs.values_list("overall_score", flat=True))
    total_scored = len(all_scores)

    avg_score = round(sum(all_scores) / total_scored, 1) if total_scored else 0
    grade_a_count = sum(1 for s in all_scores if s >= 75)
    below_50_count = sum(1 for s in all_scores if s < 50)

    total_senators = Senator.objects.filter(is_deceased=False).count()
    still_computing = Senator.objects.filter(is_still_computing=True, is_deceased=False).count()

    stats = {
        "total_senators": total_senators,
        "avg_score": avg_score,
        "grade_a_pct": round(grade_a_count / total_scored * 100) if total_scored else 0,
        "below_50_pct": round(below_50_count / total_scored * 100) if total_scored else 0,
        "still_computing": still_computing,
    }

    # Top 5 performers
    top_performers = []
    for perf in (
        scored_qs.order_by("-overall_score")[:5]
    ):
        s = perf.senator
        county_fk = getattr(s, "county_fk", None)
        top_performers.append({
            "senator_id": s.senator_id,
            "name": s.name,
            "county": getattr(county_fk, "name", "—"),
            "party": s.party or "",
            "grade": perf.grade or "—",
            "overall_score": perf.overall_score or 0,
            "display_image_url": s.display_image_url,
        })

    # Nominated senators gap
    nominated_avg = (
        scored_qs.filter(senator__nomination__isnull=False)
        .exclude(senator__nomination="")
        .aggregate(avg=Avg("overall_score"))["avg"]
    ) or 0
    elected_avg = (
        scored_qs.filter(Q(senator__nomination__isnull=True) | Q(senator__nomination=""))
        .aggregate(avg=Avg("overall_score"))["avg"]
    ) or 0
    nominated_gap = round(elected_avg - nominated_avg, 1) if nominated_avg and elected_avg else None

    # Attendance stats (sessions_attended field)
    sess_values = list(
        active_qs.filter(sessions_attended__isnull=False, sessions_attended__gt=0)
        .values_list("sessions_attended", flat=True)
        .order_by("sessions_attended")
    )
    attendance_stats = None
    if sess_values:
        n = len(sess_values)
        q1_end = n // 4
        q3_start = (3 * n) // 4
        bottom_vals = sess_values[:q1_end] if q1_end else sess_values[:1]
        top_vals = sess_values[q3_start:] if q3_start < n else sess_values[-1:]
        median_val = sess_values[n // 2]
        attendance_stats = {
            "top_quartile_avg": round(sum(top_vals) / len(top_vals)),
            "bottom_quartile_avg": round(sum(bottom_vals) / len(bottom_vals)),
            "median_avg": median_val,
            "gap": round(sum(top_vals) / len(top_vals)) - round(sum(bottom_vals) / len(bottom_vals)),
        }

    # Bills stats
    bills_data = list(
        active_qs.values_list("sponsored_bills", flat=True).filter(sponsored_bills__isnull=False)
    )
    bills_stats = None
    if bills_data and total_scored:
        zero_bills = sum(1 for b in bills_data if b == 0)
        total_bills_sum = sum(bills_data)
        n_b = len(bills_data)
        sorted_bills = sorted(bills_data, reverse=True)
        top_10_n = max(1, n_b // 10)
        top_10_bills = sum(sorted_bills[:top_10_n])
        bills_stats = {
            "zero_bills_pct": round(zero_bills / n_b * 100) if n_b else 0,
            "top_10_pct": round(top_10_n / n_b * 100) if n_b else 0,
            "top_10_bills_pct": round(top_10_bills / total_bills_sum * 100) if total_bills_sum else 0,
        }

    # Grade distribution for bar chart
    bands = [
        ("E", 0, 29, "#94a3b8", 0),
        ("D", 30, 44, "#f87171", 0),
        ("C", 45, 59, "#fbbf24", 0),
        ("B", 60, 74, "#60a5fa", 0),
        ("A", 75, 100, "#34d399", 0),
    ]
    grade_dist = []
    max_count = 1
    for label, lo, hi, color, _ in bands:
        cnt = sum(1 for s in all_scores if lo <= s <= hi)
        max_count = max(max_count, cnt)
        grade_dist.append({"label": label, "count": cnt, "color": color})
    for band in grade_dist:
        band["bar_height"] = round(band["count"] / max_count * 48) if max_count else 4

    featured = {
        "period": "Q1 2026",
        "title": "Top Performers Dominate Debate Pillar — Not Just Attendance",
        "summary": (
            "Analysis of the 2025 Hansard data shows that senators with the highest SPM scores "
            "consistently lead on both the Debate pillar (words + speeches + motions) AND the "
            "Structural pillar (attendance + voting + bills). High attendance alone is not sufficient "
            "for a top grade — active debate participation is the differentiating factor."
        ),
        "stat": f"{stats['avg_score']}",
        "stat_label": "average SPM score across the Senate",
    }

    return render(request, "scorecard/findings.html", {
        "stats": stats,
        "top_performers": top_performers,
        "nominated_gap": nominated_gap,
        "attendance_stats": attendance_stats,
        "bills_stats": bills_stats,
        "grade_dist": grade_dist,
        "featured": featured,
    })


def service_worker(request):
    """Serve the service worker at /sw.js for PWA scope (root)."""
    path = Path(settings.BASE_DIR) / "scorecard" / "static" / "scorecard" / "sw.js"
    if not path.exists():
        return HttpResponse("", status=404)
    return HttpResponse(path.read_bytes(), content_type="application/javascript")

