from django.test import TestCase

from scorecard.models import Senator, ParliamentaryPerformance, County


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
