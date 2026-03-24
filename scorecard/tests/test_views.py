from django.test import TestCase, Client
from django.urls import reverse

from scorecard.models import Senator, ParliamentaryPerformance, County


class SecurityValidationTest(TestCase):
    """Unit tests for sanitization and validation of URL/GET params."""

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


class ViewsTest(TestCase):
    """Tests for scorecard views."""

    def setUp(self):
        self.client = Client()
        self.county, _ = County.objects.get_or_create(
            slug="nairobi",
            defaults={"name": "Nairobi", "region": "central", "description": "Test county"},
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
        response = self.client.get(reverse("scorecard:home"))
        self.assertEqual(response.status_code, 200)

    def test_senator_list_returns_200(self):
        response = self.client.get(reverse("scorecard:senator-list"))
        self.assertEqual(response.status_code, 200)

    def test_senator_detail_returns_200(self):
        response = self.client.get(
            reverse("scorecard:senator-detail", kwargs={"senator_id": "john-doe"})
        )
        self.assertEqual(response.status_code, 200)

    def test_senator_detail_404_for_invalid_id(self):
        response = self.client.get(
            reverse("scorecard:senator-detail", kwargs={"senator_id": "nonexistent"})
        )
        self.assertEqual(response.status_code, 404)

    def test_about_returns_200(self):
        response = self.client.get(reverse("scorecard:about"))
        self.assertEqual(response.status_code, 200)

    def test_compare_returns_200(self):
        response = self.client.get(reverse("scorecard:compare-senators"))
        self.assertEqual(response.status_code, 200)

    def test_compare_with_ids(self):
        response = self.client.get(
            reverse("scorecard:compare-senators") + "?ids=john-doe"
        )
        self.assertEqual(response.status_code, 200)


class CountyAndInsightsViewsTest(TestCase):
    """Additional coverage for county, insights, and engine partial flows."""

    def setUp(self):
        self.client = Client()
        self.county, _ = County.objects.get_or_create(
            slug="mombasa",
            defaults={"name": "Mombasa", "region": "coast", "description": "Coastal county"},
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
        resp_list = self.client.get(reverse("scorecard:county-list"))
        self.assertEqual(resp_list.status_code, 200)
        self.assertIn(self.county, resp_list.context["counties"])

        resp_detail = self.client.get(
            reverse("scorecard:county-detail", kwargs={"slug": self.county.slug})
        )
        self.assertEqual(resp_detail.status_code, 200)
        senators = resp_detail.context["senators"]
        self.assertTrue(any(s["senator_id"] == self.senator.senator_id for s in senators))

    def test_data_insights_metrics_and_charts(self):
        resp = self.client.get(reverse("scorecard:data-insights"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("metrics", resp.context)
        self.assertIn("charts_json", resp.context)

    def test_engine_partial_parliamentary(self):
        resp = self.client.get(
            reverse(
                "scorecard:engine-partial",
                kwargs={"senator_id": self.senator.senator_id, "engine_type": "parliamentary"},
            )
        )
        self.assertEqual(resp.status_code, 200)

    def test_engine_partial_placeholder_for_unknown_engine(self):
        resp = self.client.get(
            reverse(
                "scorecard:engine-partial",
                kwargs={"senator_id": self.senator.senator_id, "engine_type": "unknown"},
            )
        )
        self.assertEqual(resp.status_code, 200)

    def test_frontier_insights_returns_200(self):
        resp = self.client.get(reverse("scorecard:frontier-insights"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("senators_display", resp.context)


class SecurityHardeningTest(TestCase):
    """Verify production security hardening configurations."""

    def test_export_csv_requires_staff(self):
        """Export CSV should redirect to login for unauthenticated users."""
        url = reverse("scorecard:insights-export-csv")
        response = self.client.get(url)
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
        with self.settings(DEBUG=False):
            response = self.client.get(reverse("scorecard:home"))
            self.assertEqual(response.status_code, 200)
            self.assertIn("Content-Security-Policy", response)
            self.assertEqual(response["X-Frame-Options"], "DENY")
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")
