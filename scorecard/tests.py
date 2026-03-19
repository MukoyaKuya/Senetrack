from django.test import TestCase, Client
from django.urls import reverse

from .models import Senator, ParliamentaryPerformance, County
from .engine import (
    HansardEngine,
    SenatorPerformanceEngine,
    get_engine_result,
    perf_to_engine_data,
)


class SenatorPerformanceEngineTest(TestCase):
    """Tests for the WMFA performance engine."""

    def test_calculate_returns_expected_structure(self):
        data = {
            "speeches": 300,
            "attendance_rate": 90.0,
            "sponsored_bills": 2,
            "passed_bills": 1,
            "amendments": 5,
            "committee_role": "Member",
            "committee_attendance": 85.0,
            "total_votes": 20,
            "attended_votes": 18,
            "oversight_actions": 3,
            "county_representation": 8.0,
        }
        result = SenatorPerformanceEngine.calculate(data)
        self.assertIn("overall_score", result)
        self.assertIn("grade", result)
        self.assertIn("grade_text", result)
        self.assertIn("pillars", result)
        self.assertIn("percentages", result)
        self.assertIn("insights", result)

    def test_score_bounds(self):
        result = SenatorPerformanceEngine.calculate({
            "speeches": 0,
            "attendance_rate": 0,
            "sponsored_bills": 0,
            "passed_bills": 0,
            "amendments": 0,
            "committee_role": "None",
            "committee_attendance": 0,
            "total_votes": 20,
            "attended_votes": 0,
            "oversight_actions": 0,
            "county_representation": 0,
        })
        self.assertGreaterEqual(result["overall_score"], 0)
        self.assertLessEqual(result["overall_score"], 100)

    def test_grade_assignment(self):
        # High performer -> A range
        high = SenatorPerformanceEngine.calculate({
            "speeches": 1000,
            "attendance_rate": 98.0,
            "sponsored_bills": 10,
            "passed_bills": 5,
            "amendments": 20,
            "committee_role": "Chair",
            "committee_attendance": 95.0,
            "total_votes": 20,
            "attended_votes": 20,
            "oversight_actions": 10,
            "county_representation": 10.0,
        })
        self.assertIn(high["grade"], ["A", "A-", "B+"])

    def test_new_status_when_attendance_negative(self):
        """Negative attendance_rate should trigger the NEW/STILL COMPUTING status."""
        result = SenatorPerformanceEngine.calculate({
            "speeches": 0,
            "attendance_rate": -1.0,
            "sponsored_bills": 0,
            "passed_bills": 0,
            "amendments": 0,
            "committee_role": "None",
            "committee_attendance": 0,
            "total_votes": 0,
            "attended_votes": 0,
            "oversight_actions": 0,
            "county_representation": 0,
        })
        self.assertEqual(result["grade"], "NEW")
        self.assertEqual(result["grade_text"], "STILL COMPUTING")

    def test_perf_to_engine_data_none(self):
        self.assertIsNone(perf_to_engine_data(None))

    def test_perf_to_engine_data_mapping(self):
        county = County.objects.create(
            name="Test County",
            slug="test-county",
            region="central",
        )
        senator = Senator.objects.create(
            senator_id="test-senator",
            name="Test Senator",
            county_fk=county,
            party="Test Party",
        )
        perf = ParliamentaryPerformance.objects.create(
            senator=senator,
            speeches=100,
            attendance_rate=85.0,
            sponsored_bills=2,
            county_representation_score=8.0,
        )
        data = perf_to_engine_data(perf)
        self.assertIsNotNone(data)
        self.assertEqual(data["speeches"], 100)
        self.assertEqual(data["attendance_rate"], 85.0)
        self.assertEqual(data["sponsored_bills"], 2)
        self.assertEqual(data["county_representation"], 8.0)


class ViewsTest(TestCase):
    """Tests for scorecard views."""

    def setUp(self):
        self.client = Client()
        self.county, _ = County.objects.get_or_create(
            slug="nairobi",
            defaults={
                "name": "Nairobi",
                "region": "central",
                "description": "Test county",
            },
        )
        self.senator = Senator.objects.create(
            senator_id="john-doe",
            name="John Doe",
            county_fk=self.county,
            party="Test Party",
        )
        ParliamentaryPerformance.objects.create(
            senator=self.senator,
            speeches=200,
            attendance_rate=90.0,
            sponsored_bills=1,
            passed_bills=0,
            amendments=3,
            total_votes=20,
            attended_votes=18,
            county_representation_score=8.0,
        )

    def test_home_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_senator_list_returns_200(self):
        response = self.client.get(reverse("senator-list"))
        self.assertEqual(response.status_code, 200)

    def test_senator_detail_returns_200(self):
        response = self.client.get(
            reverse("senator-detail", kwargs={"senator_id": "john-doe"})
        )
        self.assertEqual(response.status_code, 200)

    def test_senator_detail_404_for_invalid_id(self):
        response = self.client.get(
            reverse("senator-detail", kwargs={"senator_id": "nonexistent"})
        )
        self.assertEqual(response.status_code, 404)

    def test_about_returns_200(self):
        response = self.client.get(reverse("about"))
        self.assertEqual(response.status_code, 200)

    def test_compare_returns_200(self):
        response = self.client.get(reverse("compare-senators"))
        self.assertEqual(response.status_code, 200)

    def test_compare_with_ids(self):
        response = self.client.get(
            reverse("compare-senators") + "?ids=john-doe"
        )
        self.assertEqual(response.status_code, 200)


class CountyAndInsightsViewsTest(TestCase):
    """Additional coverage for county, insights, and engine partial flows."""

    def setUp(self):
        self.client = Client()
        self.county, _ = County.objects.get_or_create(
            slug="mombasa",
            defaults={
                "name": "Mombasa",
                "region": "coast",
                "description": "Coastal county",
            },
        )
        self.senator = Senator.objects.create(
            senator_id="coast-senator",
            name="Coast Senator",
            county_fk=self.county,
            party="Ocean Party",
        )
        self.perf = ParliamentaryPerformance.objects.create(
            senator=self.senator,
            speeches=150,
            attendance_rate=88.0,
            sponsored_bills=1,
            passed_bills=1,
            amendments=2,
            total_votes=20,
            attended_votes=17,
            county_representation_score=7.0,
        )

    def test_county_list_and_detail(self):
        resp_list = self.client.get(reverse("county-list"))
        self.assertEqual(resp_list.status_code, 200)
        self.assertIn(self.county, resp_list.context["counties"])

        resp_detail = self.client.get(
            reverse("county-detail", kwargs={"slug": self.county.slug})
        )
        self.assertEqual(resp_detail.status_code, 200)
        senators = resp_detail.context["senators"]
        self.assertTrue(any(s["senator_id"] == self.senator.senator_id for s in senators))

    def test_data_insights_metrics_and_charts(self):
        resp = self.client.get(reverse("data-insights"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("metrics", resp.context)
        self.assertIn("charts_json", resp.context)

    def test_engine_partial_parliamentary(self):
        resp = self.client.get(
            reverse(
                "engine-partial",
                kwargs={"senator_id": self.senator.senator_id, "engine_type": "parliamentary"},
            )
        )
        self.assertEqual(resp.status_code, 200)

    def test_engine_partial_placeholder_for_unknown_engine(self):
        resp = self.client.get(
            reverse(
                "engine-partial",
                kwargs={"senator_id": self.senator.senator_id, "engine_type": "unknown"},
            )
        )
        self.assertEqual(resp.status_code, 200)

    def test_frontier_insights_returns_200(self):
        resp = self.client.get(reverse("frontier-insights"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("senators_display", resp.context)


class HansardEngineTest(TestCase):
    """Tests for Hansard 2025 performance engine."""

    def test_calculate_returns_expected_structure(self):
        data = {
            "total_votes": 20,
            "attended_votes": 18,
            "sessions_attended": 80,
            "sponsored_bills": 5,
            "words_spoken": 20000,
            "speeches": 500,
            "motions_sponsored": 5,
            "statements_2025": 10,
            "county_representation": 8.0,
            "is_nominated": False,
        }
        result = HansardEngine.calculate(data)
        self.assertIn("overall_score", result)
        self.assertIn("grade", result)
        self.assertIn("structural_score", result)
        self.assertIn("debate_score", result)
        self.assertIn("pillars", result)

    def test_score_bounds(self):
        result = HansardEngine.calculate({
            "total_votes": 20,
            "attended_votes": 0,
            "sessions_attended": 0,
            "sponsored_bills": 0,
            "words_spoken": 0,
            "speeches": 0,
            "motions_sponsored": 0,
            "county_representation": 0,
            "is_nominated": False,
        })
        self.assertGreaterEqual(result["overall_score"], 0)
        self.assertLessEqual(result["overall_score"], 100)


class GetEngineResultTest(TestCase):
    """Tests for get_engine_result (Hansard vs legacy branching)."""

    def setUp(self):
        self.county = County.objects.create(
            name="Test County",
            slug="test-county",
            region="central",
        )
        self.senator = Senator.objects.create(
            senator_id="eng-test",
            name="Engine Test",
            county_fk=self.county,
            party="Party",
        )

    def test_returns_none_for_none_perf(self):
        self.assertIsNone(get_engine_result(None))

    def test_returns_legacy_engine_when_no_hansard_data(self):
        perf = ParliamentaryPerformance.objects.create(
            senator=self.senator,
            speeches=100,
            attendance_rate=85.0,
            sponsored_bills=2,
            total_votes=20,
            attended_votes=18,
            county_representation_score=7.0,
        )
        result = get_engine_result(perf)
        self.assertIsNotNone(result)
        self.assertIn("overall_score", result)
        self.assertIn("grade", result)
        self.assertIn("pillars", result)
        self.assertIn("insights", result)

    def test_returns_hansard_engine_when_hansard_data_present(self):
        perf = ParliamentaryPerformance.objects.create(
            senator=self.senator,
            speeches=200,
            words_spoken=10000,
            sessions_attended=50,
            motions_sponsored=3,
            total_votes=20,
            attended_votes=19,
            county_representation_score=8.0,
        )
        result = get_engine_result(perf)
        self.assertIsNotNone(result)
        self.assertIn("overall_score", result)
        self.assertIn("grade", result)
        self.assertIn("pillars", result)


class AnalyticsTest(TestCase):
    """Tests for analytics service."""

    def test_normalize_frontier(self):
        from scorecard.services.analytics import normalize_frontier
        self.assertEqual(normalize_frontier("Western"), "western")
        self.assertEqual(normalize_frontier("Rift Valley"), "rift_valley")
        self.assertEqual(normalize_frontier(""), "")
        self.assertEqual(normalize_frontier("  coast  "), "coast")

    def test_build_senator_rows_empty_when_no_perf(self):
        from scorecard.services.analytics import build_senator_rows
        county = County.objects.create(name="Empty", slug="empty", region="other")
        Senator.objects.create(
            senator_id="no-perf",
            name="No Perf",
            county_fk=county,
            party="X",
        )
        rows = build_senator_rows()
        senator_ids = [r["senator_id"] for r in rows]
        self.assertNotIn("no-perf", senator_ids)

    def test_build_senator_rows_includes_row_when_perf_exists(self):
        from scorecard.services.analytics import build_senator_rows
        county = County.objects.create(name="HasPerf", slug="has-perf", region="central")
        sen = Senator.objects.create(
            senator_id="has-perf",
            name="Has Perf",
            county_fk=county,
            party="Y",
        )
        ParliamentaryPerformance.objects.create(
            senator=sen,
            speeches=10,
            attendance_rate=80.0,
            total_votes=20,
            attended_votes=16,
            county_representation_score=5.0,
        )
        rows = build_senator_rows()
        senator_ids = [r["senator_id"] for r in rows]
        self.assertIn("has-perf", senator_ids)
        row = next(r for r in rows if r["senator_id"] == "has-perf")
        self.assertIn("overall_score", row)
        self.assertIn("frontier", row)
        self.assertEqual(row["frontier"], "central")


class SecurityValidationTest(TestCase):
    """Sanitization and validation for URL/GET params."""

    def test_sanitize_senator_id_accepts_valid(self):
        from scorecard.security import sanitize_senator_id
        self.assertEqual(sanitize_senator_id("cheruiyot-aaron"), "cheruiyot-aaron")
        self.assertEqual(sanitize_senator_id("john_doe"), "john_doe")

    def test_sanitize_senator_id_rejects_invalid(self):
        from scorecard.security import sanitize_senator_id
        self.assertIsNone(sanitize_senator_id(""))
        self.assertIsNone(sanitize_senator_id("id/../admin"))
        self.assertIsNone(sanitize_senator_id("<script>"))
        self.assertIsNone(sanitize_senator_id("a" * 51))

    def test_sanitize_senator_ids_caps_count(self):
        from scorecard.security import sanitize_senator_ids
        ids = ["a", "b", "c", "d", "e", "f"]
        out = sanitize_senator_ids(ids, max_count=5)
        self.assertEqual(len(out), 5)


class CountyFrontierTest(TestCase):
    """Tests for county/frontier normalization service."""

    def test_build_county_maps_applies_aliases(self):
        from scorecard.services.county_frontier import build_county_maps
        counties = [
            {"name": "Murang'a", "region": "central", "slug": "muranga"},
            {"name": "Taita-Taveta", "region": "coast", "slug": "taita-taveta"},
        ]
        region_map, slug_map = build_county_maps(counties)
        self.assertEqual(region_map.get("Muranga"), "central")
        self.assertEqual(region_map.get("Murang'a"), "central")
        self.assertEqual(slug_map.get("Muranga"), "muranga")
        self.assertEqual(region_map.get("Taita Taveta"), "coast")

    def test_resolve_region_exact_match(self):
        from scorecard.services.county_frontier import build_county_maps, resolve_region
        counties = [{"name": "Nairobi", "region": "central", "slug": "nairobi"}]
        region_map, _ = build_county_maps(counties)
        self.assertEqual(resolve_region("Nairobi", region_map), "central")

    def test_resolve_region_returns_none_for_empty(self):
        from scorecard.services.county_frontier import resolve_region
        self.assertIsNone(resolve_region("", {}))
        self.assertIsNone(resolve_region(None, {}))


class InsightsChartsTest(TestCase):
    """Tests for insights chart-building pure function."""

    def test_build_insights_charts_returns_all_expected_keys(self):
        from scorecard.services.insights_charts import build_insights_charts
        aggregates = {
            "rows": [],
            "bins": [0] * 10,
            "frontier_chart": [],
            "top_sponsored": [],
            "committee_leadership_impact": {"leaders_avg": 0, "members_avg": 0, "leaders_count": 0, "members_count": 0},
            "county_performance": [],
            "grade_distribution": [],
            "committee_role_stats": [],
            "party_performance": [],
            "frontier_by_metric": [],
            "nominated": [],
            "elected": [],
            "nom_avg_score": 0.0,
            "elec_avg_score": 0.0,
            "nom_avg_att": 0.0,
            "elec_avg_att": 0.0,
            "grade_tier_stats": [],
            "sorted_rows": [],
        }
        charts = build_insights_charts(aggregates)
        expected = [
            "score_distribution", "frontier_scores", "attendance_vs_score",
            "bills_sponsored_vs_passed", "speeches_vs_score", "words_vs_score",
            "structural_vs_debate", "amendments_vs_passed", "grade_distribution",
            "committee_role_chart", "party_performance", "frontier_by_metric",
            "nominated_vs_elected", "committee_leadership", "county_performance",
            "grade_tier_stats",
        ]
        for key in expected:
            self.assertIn(key, charts, msg=f"Missing chart key: {key}")

    def test_build_insights_charts_with_sample_data(self):
        from scorecard.services.insights_charts import build_insights_charts
        row = {
            "name": "Sen A",
            "overall_score": 75,
            "attendance_rate": 90,
            "speeches": 100,
            "words_spoken": 5000,
            "structural_score": 40,
            "debate_score": 35,
            "sponsored_bills": 2,
            "passed_bills": 1,
            "amendments": 1,
        }
        aggregates = {
            "rows": [row],
            "bins": [0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
            "frontier_chart": [{"frontier": "central", "avg_score": 75}],
            "top_sponsored": [row],
            "committee_leadership_impact": {"leaders_avg": 80, "members_avg": 70, "leaders_count": 1, "members_count": 0},
            "county_performance": [{"county": "Central", "avg_score": 75, "avg_attendance": 90, "avg_bills": 3}],
            "grade_distribution": [{"grade": "B", "count": 1}],
            "committee_role_stats": [{"role": "Member", "count": 1, "avg_score": 75}],
            "party_performance": [{"party": "Jubilee", "count": 1, "avg_score": 75}],
            "frontier_by_metric": [{"frontier": "central", "avg_score": 75, "avg_attendance": 90, "avg_bills": 3, "avg_speeches": 100, "avg_words": 5000}],
            "nominated": [],
            "elected": [row],
            "nom_avg_score": 0.0,
            "elec_avg_score": 75.0,
            "nom_avg_att": 0.0,
            "elec_avg_att": 90.0,
            "grade_tier_stats": [{"grade": "B", "avg_words": 5000, "avg_speeches": 100, "avg_motions": 0, "avg_structural": 40, "avg_debate": 35}],
            "sorted_rows": [row],
        }
        charts = build_insights_charts(aggregates)
        self.assertEqual(charts["score_distribution"]["counts"], [0, 0, 0, 0, 0, 0, 0, 1, 0, 0])
        self.assertEqual(charts["frontier_scores"]["scores"], [75])
        self.assertEqual(charts["nominated_vs_elected"]["avg_scores"], [0.0, 75.0])
        self.assertEqual(len(charts["structural_vs_debate"]["labels"]), 1)

class SecurityHardeningTest(TestCase):
    """Verify production security hardening configurations."""

    def test_export_csv_requires_staff(self):
        """Export CSV should redirect to login for unauthenticated users."""
        url = reverse("insights-export-csv")
        response = self.client.get(url)
        # staff_member_required redirects to login with ?next=...
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_robots_txt_publicly_accessible(self):
        """Robots.txt should be served and contain Disallow rules."""
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        content = response.content.decode()
        self.assertIn("User-agent: *", content)
        self.assertIn("Disallow:", content)

    def test_security_headers_present_in_production(self):
        """Basic security headers should be present when DEBUG is False."""
        # Force DEBUG=False for this test (if not already)
        with self.settings(DEBUG=False):
            response = self.client.get(reverse("home"))
            self.assertEqual(response.status_code, 200)
            self.assertIn("Content-Security-Policy", response)
            self.assertEqual(response["X-Frame-Options"], "DENY")
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")
