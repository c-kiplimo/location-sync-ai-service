"""
Tests for Quality Scorer Service
"""
import pytest
from app.models.schemas import LocationSnapshot, Coordinates, Address
from app.services.quality_scorer import QualityScorer


@pytest.fixture
def quality_scorer():
    """Create quality scorer instance"""
    return QualityScorer()


@pytest.fixture
def perfect_snapshot():
    """Create a perfect quality snapshot"""
    return LocationSnapshot(
        locationId=1001,
        name="Perfect Restaurant",
        coordinates=Coordinates(latitude=-1.286389, longitude=36.817223),
        address=Address(
            street="123 Test Street",
            city="Nairobi",
            state="Nairobi County",
            postalCode="00100",
            country="Kenya"
        ),
        phone="+254712345678",
        openingHours={"Monday": "09:00-18:00", "Tuesday": "09:00-18:00"},
        categories=["Restaurant", "Cafe"],
        website="https://test.com",
        description="A wonderful restaurant with great food"
    )


@pytest.fixture
def minimal_snapshot():
    """Create a minimal quality snapshot"""
    return LocationSnapshot(
        locationId=1002,
        name="Minimal",
        coordinates=Coordinates(latitude=0, longitude=0)
    )


class TestQualityScorer:
    """Test quality scoring functionality"""

    def test_perfect_snapshot_scores_high(self, quality_scorer, perfect_snapshot):
        """Perfect snapshot should score 100"""
        result = quality_scorer.calculate_quality_score(perfect_snapshot)

        assert result.overallScore >= 80, "Perfect snapshot should score high"
        assert result.severity.value == "LOW"
        assert len(result.issues) <= 1  # Maybe missing opening hours

    def test_minimal_snapshot_scores_low(self, quality_scorer, minimal_snapshot):
        """Minimal snapshot should score low"""
        result = quality_scorer.calculate_quality_score(minimal_snapshot)

        assert result.overallScore < 60, "Minimal snapshot should score low"
        assert result.severity.value in ["CRITICAL", "HIGH", "MEDIUM"]
        assert len(result.issues) > 0

    def test_null_island_detected(self, quality_scorer, minimal_snapshot):
        """Should detect null island (0,0) coordinates"""
        result = quality_scorer.calculate_quality_score(minimal_snapshot)

        null_island_issues = [
            issue for issue in result.issues
            if "0,0" in issue.description or "null island" in issue.description.lower()
        ]
        assert len(null_island_issues) > 0, "Should detect null island"

    def test_missing_address_penalized(self, quality_scorer):
        """Missing address should be penalized"""
        snapshot = LocationSnapshot(
            locationId=1003,
            name="No Address Location",
            coordinates=Coordinates(latitude=-1.286389, longitude=36.817223)
        )

        result = quality_scorer.calculate_quality_score(snapshot)

        assert result.breakdown["address"] == 0
        address_issues = [
            issue for issue in result.issues
            if issue.field == "address"
        ]
        assert len(address_issues) > 0

    def test_missing_name_penalized(self, quality_scorer):
        """Missing name should be penalized"""
        snapshot = LocationSnapshot(
            locationId=1004,
            coordinates=Coordinates(latitude=-1.286389, longitude=36.817223)
        )

        result = quality_scorer.calculate_quality_score(snapshot)

        name_issues = [
            issue for issue in result.issues
            if issue.field == "name"
        ]
        assert len(name_issues) > 0
        assert result.breakdown["keywords"] < 20

    def test_breakdown_components_sum_to_total(self, quality_scorer, perfect_snapshot):
        """Breakdown components should sum to overall score"""
        result = quality_scorer.calculate_quality_score(perfect_snapshot)

        breakdown_sum = sum(result.breakdown.values())
        assert breakdown_sum == result.overallScore

    def test_consistency_with_historical(self, quality_scorer, perfect_snapshot):
        """Should detect consistency issues"""
        # Move location 2km away
        modified_snapshot = LocationSnapshot(
            locationId=perfect_snapshot.locationId,
            name=perfect_snapshot.name,
            coordinates=Coordinates(latitude=-1.3, longitude=36.85),  # ~2km away
            address=perfect_snapshot.address,
            phone=perfect_snapshot.phone
        )

        result = quality_scorer.calculate_quality_score(
            modified_snapshot,
            historical=perfect_snapshot
        )

        # Should have consistency issue
        consistency_score = result.breakdown["consistency"]
        assert consistency_score < 20, "Should detect coordinate movement"