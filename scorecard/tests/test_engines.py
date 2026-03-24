from django.test import TestCase

from scorecard.models import Senator, ParliamentaryPerformance, County
from scorecard.engine import (
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
        county = County.objects.create(name="Test County", slug="test-county", region="central")
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
        self.county = County.objects.create(name="Test County", slug="test-county", region="central")
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
