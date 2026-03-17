from django.core.cache import cache
from django.db import connection
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_page

from scorecard.engine import get_engine_result, perf_to_engine_data
from scorecard.models import ParliamentaryPerformance, Senator, Party, SenatorQuote, VotingRecord
from scorecard.security import sanitize_engine_type, sanitize_senator_id, sanitize_senator_ids
from scorecard.services.senators import build_senator_display

RANKING_CACHE_KEY = "senator_ranking_data_v3"
RANKING_CACHE_TIMEOUT = 300  # 5 min


def _get_ranking_data():
    """Cached list of (senator_id, overall_score, attendance_rate, name) ordered by score then attendance."""
    data = cache.get(RANKING_CACHE_KEY)
    if data is not None:
        return data
    rows = list(
        ParliamentaryPerformance.objects.select_related("senator")
        .order_by("-overall_score", "-attendance_rate")
        .values_list("senator__senator_id", "overall_score", "attendance_rate", "senator__name")
    )
    cache.set(RANKING_CACHE_KEY, rows, RANKING_CACHE_TIMEOUT)
    return rows


# Static voting history records from public sources (Mzalendo / Parliament)
VOTING_HISTORY = {
    "samson-kiprotich-cherargei": [
        {
            "date": "October 12, 2023",
            "title": "The Social Health Insurance Bill (National Assembly Bill No. 58 of 2023)",
            "decision": "Yes",
        },
        {
            "date": "March 14, 2024",
            "title": "Kisii Deputy Governor Impeachment - Grounds 4",
            "decision": "No",
        },
        {
            "date": "March 14, 2024",
            "title": "Kisii Deputy Governor Impeachment - Grounds 3",
            "decision": "No",
        },
        {
            "date": "March 14, 2024",
            "title": "Kisii Deputy Governor Impeachment - Grounds 2",
            "decision": "No",
        },
        {
            "date": "March 14, 2024",
            "title": "Kisii Deputy Governor Impeachment - Grounds 1",
            "decision": "No",
        },
        {
            "date": "August 14, 2025",
            "title": "The County Governments Allocation Bill, 2025 (Committee of the Whole)",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Business Laws (Amendment) Bill 2024",
            "decision": "Yes",
        },
        {
            "date": "October 29, 2024",
            "title": "Sugar Bill",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 11",
            "decision": "No",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 10",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 9",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 8",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 7",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 6",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 5",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 4",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 3",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 2",
            "decision": "No",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 1",
            "decision": "Yes",
        },
        {
            "date": "March 12, 2024",
            "title": "Affordable Housing Bill 2024",
            "decision": "Yes",
        },
    ],
    "aaron-cheruiyot": [
        {
            "date": "October 12, 2023",
            "title": "The Social Health Insurance Bill (National Assembly Bill No. 58 of 2023)",
            "decision": "Yes",
        },
        {
            "date": "March 14, 2024",
            "title": "Kisii Deputy Governor Impeachment - Grounds 4",
            "decision": "No",
        },
        {
            "date": "March 14, 2024",
            "title": "Kisii Deputy Governor Impeachment - Grounds 3",
            "decision": "No",
        },
        {
            "date": "March 14, 2024",
            "title": "Kisii Deputy Governor Impeachment - Grounds 2",
            "decision": "No",
        },
        {
            "date": "March 14, 2024",
            "title": "Kisii Deputy Governor Impeachment - Grounds 1",
            "decision": "No",
        },
        {
            "date": "August 14, 2025",
            "title": "The County Governments Allocation Bill, 2025 (Committee of the Whole)",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Business Laws (Amendment) Bill 2024",
            "decision": "Yes",
        },
        {
            "date": "October 29, 2024",
            "title": "Sugar Bill",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 11",
            "decision": "No",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 10",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 9",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 8",
            "decision": "No",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 7",
            "decision": "No",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 6",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 5",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 4",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 3",
            "decision": "No",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 2",
            "decision": "Yes",
        },
        {
            "date": "October 17, 2024",
            "title": "Rigathi Gachagua Impeachment - Grounds 1",
            "decision": "Yes",
        },
        {
            "date": "March 12, 2024",
            "title": "Affordable Housing Bill 2024",
            "decision": "Yes",
        },
    ],
    "murungi-kathuri": [
        {"date": "October 12, 2023", "title": "The Social Health Insurance Bill (National Assembly Bill No. 58 of 2023)", "decision": "Yes"},
        {"date": "March 14, 2024", "title": "Kisii Deputy Governor Impeachment - Grounds 4", "decision": "Yes"},
        {"date": "March 14, 2024", "title": "Kisii Deputy Governor Impeachment - Grounds 3", "decision": "Yes"},
        {"date": "March 14, 2024", "title": "Kisii Deputy Governor Impeachment - Grounds 2", "decision": "Yes"},
        {"date": "March 14, 2024", "title": "Kisii Deputy Governor Impeachment - Grounds 1", "decision": "Yes"},
        {"date": "August 14, 2025", "title": "The County Governments Allocation Bill, 2025 (Committee of the Whole)", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Business Laws (Amendment) Bill 2024", "decision": "Yes"},
        {"date": "October 29, 2024", "title": "Sugar Bill", "decision": "Absent"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 11", "decision": "No"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 10", "decision": "No"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 9", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 8", "decision": "No"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 7", "decision": "No"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 6", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 5", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 4", "decision": "No"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 3", "decision": "No"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 2", "decision": "No"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 1", "decision": "Yes"},
        {"date": "March 12, 2024", "title": "Affordable Housing Bill 2024", "decision": "Yes"},
    ],
    "stewart-mwachiru-shadrack-madzayo": [
        {"date": "October 12, 2023", "title": "The Social Health Insurance Bill (National Assembly Bill No. 58 of 2023)", "decision": "Absent"},
        {"date": "March 14, 2024", "title": "Kisii Deputy Governor Impeachment - Grounds 4", "decision": "Yes"},
        {"date": "March 14, 2024", "title": "Kisii Deputy Governor Impeachment - Grounds 3", "decision": "Yes"},
        {"date": "March 14, 2024", "title": "Kisii Deputy Governor Impeachment - Grounds 2", "decision": "Yes"},
        {"date": "March 14, 2024", "title": "Kisii Deputy Governor Impeachment - Grounds 1", "decision": "Yes"},
        {"date": "August 14, 2025", "title": "The County Governments Allocation Bill, 2025 (Committee of the Whole)", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Business Laws (Amendment) Bill 2024", "decision": "Absent"},
        {"date": "October 29, 2024", "title": "Sugar Bill", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 11", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 10", "decision": "No"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 9", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 8", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 7", "decision": "No"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 6", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 5", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 4", "decision": "Yes"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 3", "decision": "No"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 2", "decision": "No"},
        {"date": "October 17, 2024", "title": "Rigathi Gachagua Impeachment - Grounds 1", "decision": "Yes"},
        {"date": "March 12, 2024", "title": "Affordable Housing Bill 2024", "decision": "No"},
    ],
}


def _get_voting_history_for_senator(senator):
    """
    Fetch voting history for a senator, preferring database-backed records but
    falling back to the legacy static dictionary if the table or data is absent.
    """

    table_name = VotingRecord._meta.db_table
    try:
        if table_name in connection.introspection.table_names():
            records = (
                VotingRecord.objects.filter(senator=senator)
                .order_by("-date")
                .values("date", "title", "decision")
            )
            history = []
            for r in records:
                date_val = r["date"]
                formatted_date = (
                    date_val.strftime("%B %d, %Y") if hasattr(date_val, "strftime") else str(date_val)
                )
                history.append(
                    {
                        "date": formatted_date,
                        "title": r["title"],
                        "decision": r["decision"],
                    }
                )
            if history:
                return history
    except Exception:
        # On any DB or introspection issue, defer to legacy static data.
        pass

    return VOTING_HISTORY.get(senator.senator_id, [])


def senator_detail(request, senator_id):
    """Main dashboard page."""
    clean_id = sanitize_senator_id(senator_id)
    if clean_id is None:
        raise Http404("Invalid senator identifier")
    senator = get_object_or_404(
        Senator.objects.select_related("perf").prefetch_related(
            Prefetch("quotes", queryset=SenatorQuote.objects.order_by("-date"))
        ),
        senator_id=clean_id,
    )
    perf = getattr(senator, "perf", None)
    results = get_engine_result(perf)
    if not results:
        results = {
            "overall_score": 0,
            "grade": "—",
            "grade_text": "No data",
            "pillars": {
                "participation": 0,
                "legislative": 0,
                "voting": 0,
                "committee": 0,
                "county": 0,
            },
            "percentages": {
                "participation": 0,
                "legislative": 0,
                "voting": 0,
                "committee": 0,
                "county": 0,
            },
            "insights": {"strengths": ["Performance data not yet available"], "improvements": []},
        }
    else:
        # Ensure every senator profile has meaningful insights (Hansard engine doesn't generate text insights).
        try:
            from scorecard.services.analytics import get_senator_rows
            from scorecard.services.senator_insights import build_profile_insights

            rows = get_senator_rows()
            current_row = next((r for r in rows if str(r.get("senator_id")).lower() == str(clean_id).lower()), None)
            if current_row:
                results["insights"] = build_profile_insights(current_row, rows)
            else:
                results.setdefault("insights", {"strengths": [], "improvements": []})
        except Exception:
            results.setdefault("insights", {"strengths": [], "improvements": []})

    ranking_data = _get_ranking_data()
    total_senators = len(ranking_data)
    national_rank = None
    attendance_rank = None
    national_avg_attendance = round(sum(r[2] for r in ranking_data) / total_senators, 1) if ranking_data else None

    for i, (sid, *_rest) in enumerate(ranking_data, 1):
        if str(sid).lower() == str(clean_id).lower():
            national_rank = i
            break
    by_attendance = sorted(ranking_data, key=lambda r: -r[2])
    for i, (sid, *_rest) in enumerate(by_attendance, 1):
        if str(sid).lower() == str(clean_id).lower():
            attendance_rank = i
            break

    bills_in_committee = max(0, perf.sponsored_bills - perf.passed_bills) if perf else 0

    attendance_heatmap = [
        {
            "senator_id": sid,
            "rate": round(rate, 1),
            "name": name,
            "is_current": sid == clean_id,
        }
        for sid, _score, rate, name in by_attendance
    ]

    quotes_prefetched = list(senator.quotes.all())
    latest_quote = quotes_prefetched[0] if quotes_prefetched else None
    if latest_quote:
        m = latest_quote.date.month
        y = latest_quote.date.year
        quotes_period = f"Early {y}" if m <= 3 else (f"Mid {y}" if m <= 6 else f"Late {y}")
    else:
        quotes_period = ""

    senator_display = build_senator_display(senator)

    # Party information for UI card
    party_info = None
    raw_party = (getattr(senator_display, "party", "") or "").strip()
    if raw_party:
        party_obj = Party.objects.filter(name=raw_party).first()
        if party_obj:
            # All senators currently in this party (for listing in the card)
            senate_leaders_qs = Senator.objects.filter(party=raw_party).order_by("name")
            party_info = {
                "name": party_obj.name,
                "logo_url": party_obj.logo.url if party_obj.logo else None,
                "founded_year": party_obj.founded_year,
                "leader_name": party_obj.leader_name,
                "history": party_obj.history,
                "senate_leaders": [s.name for s in senate_leaders_qs],
            }

    voting_history = _get_voting_history_for_senator(senator)

    return render(
        request,
        "scorecard/scorecard.html",
        {
            "senator": senator_display,
            "results": results,
            "national_rank": national_rank,
            "attendance_rank": attendance_rank,
            "total_senators": total_senators,
            "bills_in_committee": bills_in_committee,
            "quotes_period": quotes_period,
            "national_avg_attendance": national_avg_attendance,
            "has_national_avg": national_avg_attendance is not None,
            "attendance_heatmap": attendance_heatmap,
            "party_info": party_info,
            "voting_history": voting_history,
            "voting_history_count": len(voting_history),
        },
    )


def get_engine_partial(request, senator_id, engine_type):
    """HTMX fragment endpoint."""
    clean_id = sanitize_senator_id(senator_id)
    if clean_id is None:
        raise Http404("Invalid senator identifier")
    senator = get_object_or_404(Senator, senator_id=clean_id)
    engine_type = sanitize_engine_type(engine_type)
    if engine_type == "parliamentary":
        perf = get_object_or_404(ParliamentaryPerformance, senator=senator)
        results = get_engine_result(perf) or {}
        context = {
            "results": results,
            "perf": perf,
            "missed_votes": max(0, perf.total_votes - perf.attended_votes),
            "dash_array": f"{(results.get('pillars', {}).get('committee', 0) / 25) * 251.2} 251.2",
        }
        return render(request, "partials/parliamentary_engine.html", context)
    return render(request, "partials/placeholder.html", {"type": engine_type})  # engine_type sanitized


@cache_page(120)
def compare_senators(request):
    """Compare two or more senators side by side."""
    ids_list = request.GET.getlist("ids")
    ids_param = request.GET.get("ids", "")
    if ids_list:
        senator_ids = sanitize_senator_ids(ids_list, max_count=5)
    else:
        senator_ids = sanitize_senator_ids([x for x in ids_param.split(",") if x], max_count=5)
    senators = []
    if senator_ids:
        senators = list(Senator.objects.filter(senator_id__in=senator_ids).select_related("perf"))
    compared = []
    for s in senators:
        res = get_engine_result(getattr(s, "perf", None)) or {
            "overall_score": 0,
            "grade": "—",
            "grade_text": "No data",
            "pillars": {
                "participation": 0,
                "legislative": 0,
                "voting": 0,
                "committee": 0,
                "county": 0,
            },
        }
        compared.append(
            {
                "senator": s,
                "results": res,
                "image_url": s.image.url if s.image else (s.image_url or ""),
            }
        )

    # Enrich comparison data with rank and score deltas
    if compared:
        scores_with_index = [
            (item["results"].get("overall_score", 0) or 0, idx)
            for idx, item in enumerate(compared)
        ]
        scores_with_index.sort(key=lambda t: (-t[0], t[1]))
        leader_score, leader_idx = scores_with_index[0]
        rank_map = {idx: rank for rank, (_, idx) in enumerate(scores_with_index, start=1)}

        for idx, item in enumerate(compared):
            score = item["results"].get("overall_score", 0) or 0
            item["rank"] = rank_map.get(idx, None)
            item["diff_from_leader"] = leader_score - score
            item["is_leader"] = idx == leader_idx

    comparison_summary = {}
    if compared:
        # Overall leader by score
        leader_overall = max(compared, key=lambda c: c["results"].get("overall_score", 0))
        comparison_summary["overall_leader"] = {
            "senator": leader_overall["senator"],
            "score": leader_overall["results"].get("overall_score", 0),
            "grade": leader_overall["results"].get("grade", "—"),
        }

        # Leaders per pillar
        pillars = ["participation", "legislative", "committee", "voting", "county"]
        pillar_leaders = {}
        for key in pillars:
            # Only consider items that have pillar data
            items_with_pillar = [
                c for c in compared if c["results"].get("pillars") and key in c["results"]["pillars"]
            ]
            if not items_with_pillar:
                continue
            best = max(items_with_pillar, key=lambda c: c["results"]["pillars"].get(key, 0))
            pillar_leaders[key] = {
                "senator": best["senator"],
                "value": best["results"]["pillars"].get(key, 0),
            }
        comparison_summary["pillars"] = pillar_leaders

    return render(
        request,
        "scorecard/compare.html",
        {
            "compared": compared,
            "all_senators": Senator.objects.select_related("perf").order_by("name"),
            "comparison_summary": comparison_summary,
        },
    )

