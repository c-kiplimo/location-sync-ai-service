"""
Quality Scoring Service

Evaluates data quality of location snapshots (0-100 scale)
"""
import re
from typing import List, Optional
from app.models.schemas import (
    LocationSnapshot,
    QualityScoreResponse,
    QualityIssue,
    QualityIssueType,
    Severity,
    Coordinates,
    Address
)


class QualityScorer:
    """Calculates quality scores for location data"""

    def __init__(self):
        self.phone_pattern = re.compile(r'^\+?[1-9]\d{1,14}$')
        self.url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$',
            re.IGNORECASE
        )

    def calculate_quality_score(
        self,
        snapshot: LocationSnapshot,
        historical: Optional[LocationSnapshot] = None
    ) -> QualityScoreResponse:
        """
        Calculate overall quality score for a location snapshot

        Args:
            snapshot: Current location snapshot
            historical: Previous snapshot for consistency check

        Returns:
            Quality score with breakdown and issues
        """
        issues: List[QualityIssue] = []
        breakdown = {}

        # Validate coordinates (20 points max)
        breakdown["coordinates"] = self._validate_coordinates(snapshot.coordinates, issues)

        # Validate address (20 points max)
        breakdown["address"] = self._validate_address(snapshot.address, issues)

        # Validate opening hours (20 points max)
        breakdown["openingHours"] = self._validate_opening_hours(
            snapshot.openingHours, issues
        )

        # Validate keywords/metadata (20 points max)
        breakdown["keywords"] = self._validate_keywords(
            snapshot.name, snapshot.categories, snapshot.description, issues
        )

        # Validate consistency (20 points max)
        breakdown["consistency"] = self._validate_consistency(
            snapshot, historical, issues
        )

        # Calculate overall score
        overall_score = sum(breakdown.values())

        # Determine severity
        severity = self._calculate_severity(overall_score)

        return QualityScoreResponse(
            overallScore=overall_score,
            breakdown=breakdown,
            issues=issues,
            severity=severity
        )

    def _validate_coordinates(
        self,
        coords: Optional[Coordinates],
        issues: List[QualityIssue]
    ) -> int:
        """Validate geographic coordinates (0-20 points)"""
        if not coords:
            issues.append(QualityIssue(
                field="coordinates",
                issueType=QualityIssueType.MISSING_REQUIRED_FIELD,
                description="Coordinates are missing",
                severity=Severity.CRITICAL
            ))
            return 0

        score = 20

        # Check for null island (0,0)
        if coords.latitude == 0 and coords.longitude == 0:
            issues.append(QualityIssue(
                field="coordinates",
                issueType=QualityIssueType.IMPLAUSIBLE_VALUE,
                description="Coordinates are (0,0) - likely invalid",
                severity=Severity.HIGH
            ))
            score -= 10

        # Validate range (already validated by Pydantic, but check for edge cases)
        if abs(coords.latitude) > 85 or abs(coords.longitude) > 175:
            issues.append(QualityIssue(
                field="coordinates",
                issueType=QualityIssueType.IMPLAUSIBLE_VALUE,
                description="Coordinates are near poles or edge cases",
                severity=Severity.MEDIUM
            ))
            score -= 5

        return max(score, 0)

    def _validate_address(
        self,
        address: Optional[Address],
        issues: List[QualityIssue]
    ) -> int:
        """Validate address completeness (0-20 points)"""
        if not address:
            issues.append(QualityIssue(
                field="address",
                issueType=QualityIssueType.MISSING_REQUIRED_FIELD,
                description="Address is missing",
                severity=Severity.CRITICAL
            ))
            return 0

        score = 20

        # Check street (most important)
        if not address.street or len(address.street.strip()) < 3:
            issues.append(QualityIssue(
                field="address.street",
                issueType=QualityIssueType.INCOMPLETE_DATA,
                description="Street address is missing or too short",
                severity=Severity.HIGH
            ))
            score -= 8

        # Check city
        if not address.city:
            issues.append(QualityIssue(
                field="address.city",
                issueType=QualityIssueType.INCOMPLETE_DATA,
                description="City is missing",
                severity=Severity.MEDIUM
            ))
            score -= 5

        # Check country
        if not address.country:
            issues.append(QualityIssue(
                field="address.country",
                issueType=QualityIssueType.INCOMPLETE_DATA,
                description="Country is missing",
                severity=Severity.MEDIUM
            ))
            score -= 4

        # Check postal code
        if not address.postalCode:
            issues.append(QualityIssue(
                field="address.postalCode",
                issueType=QualityIssueType.INCOMPLETE_DATA,
                description="Postal code is missing",
                severity=Severity.LOW
            ))
            score -= 3

        return max(score, 0)

    def _validate_opening_hours(
        self,
        opening_hours: Optional[dict],
        issues: List[QualityIssue]
    ) -> int:
        """Validate opening hours (0-20 points)"""
        if not opening_hours:
            issues.append(QualityIssue(
                field="openingHours",
                issueType=QualityIssueType.MISSING_REQUIRED_FIELD,
                description="Opening hours are missing",
                severity=Severity.MEDIUM
            ))
            return 0

        score = 20

        # Check if it's empty
        if len(opening_hours) == 0:
            issues.append(QualityIssue(
                field="openingHours",
                issueType=QualityIssueType.INCOMPLETE_DATA,
                description="Opening hours are empty",
                severity=Severity.MEDIUM
            ))
            return 0

        # Basic validation - should have at least a few days
        if len(opening_hours) < 3:
            issues.append(QualityIssue(
                field="openingHours",
                issueType=QualityIssueType.INCOMPLETE_DATA,
                description=f"Opening hours only defined for {len(opening_hours)} days",
                severity=Severity.LOW
            ))
            score -= 5

        return max(score, 0)

    def _validate_keywords(
        self,
        name: Optional[str],
        categories: Optional[List[str]],
        description: Optional[str],
        issues: List[QualityIssue]
    ) -> int:
        """Validate name, categories, and description (0-20 points)"""
        score = 20

        # Check name (most important)
        if not name or len(name.strip()) < 3:
            issues.append(QualityIssue(
                field="name",
                issueType=QualityIssueType.MISSING_REQUIRED_FIELD,
                description="Name is missing or too short",
                severity=Severity.CRITICAL
            ))
            score -= 10

        # Check categories
        if not categories or len(categories) == 0:
            issues.append(QualityIssue(
                field="categories",
                issueType=QualityIssueType.MISSING_REQUIRED_FIELD,
                description="Categories are missing",
                severity=Severity.MEDIUM
            ))
            score -= 5

        # Check description
        if not description or len(description.strip()) < 10:
            issues.append(QualityIssue(
                field="description",
                issueType=QualityIssueType.INCOMPLETE_DATA,
                description="Description is missing or too short",
                severity=Severity.LOW
            ))
            score -= 3

        return max(score, 0)

    def _validate_consistency(
        self,
        current: LocationSnapshot,
        historical: Optional[LocationSnapshot],
        issues: List[QualityIssue]
    ) -> int:
        """Validate consistency with historical data (0-20 points)"""
        if not historical:
            # No historical data to compare - assume consistent
            return 20

        score = 20

        # Check for coordinate movement > 1km (suspicious)
        if current.coordinates and historical.coordinates:
            distance = self._calculate_distance(
                current.coordinates,
                historical.coordinates
            )
            if distance > 1.0:  # > 1km
                issues.append(QualityIssue(
                    field="coordinates",
                    issueType=QualityIssueType.INCONSISTENT_DATA,
                    description=f"Location moved {distance:.2f}km from previous snapshot",
                    severity=Severity.HIGH
                ))
                score -= 15
            elif distance > 0.1:  # > 100m
                issues.append(QualityIssue(
                    field="coordinates",
                    issueType=QualityIssueType.INCONSISTENT_DATA,
                    description=f"Location moved {distance:.2f}km from previous snapshot",
                    severity=Severity.MEDIUM
                ))
                score -= 5

        # Check for name change (suspicious unless intentional)
        if current.name and historical.name:
            if current.name.lower() != historical.name.lower():
                issues.append(QualityIssue(
                    field="name",
                    issueType=QualityIssueType.INCONSISTENT_DATA,
                    description="Name changed from previous snapshot",
                    severity=Severity.MEDIUM
                ))
                score -= 5

        return max(score, 0)

    def _calculate_distance(
        self,
        coords1: Coordinates,
        coords2: Coordinates
    ) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        Returns distance in kilometers
        """
        from math import radians, cos, sin, asin, sqrt

        # Convert to radians
        lat1, lon1 = radians(coords1.latitude), radians(coords1.longitude)
        lat2, lon2 = radians(coords2.latitude), radians(coords2.longitude)

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))

        # Radius of earth in kilometers
        r = 6371

        return c * r

    def _calculate_severity(self, score: int) -> Severity:
        """Determine severity based on overall score"""
        if score < 40:
            return Severity.CRITICAL
        elif score < 60:
            return Severity.HIGH
        elif score < 80:
            return Severity.MEDIUM
        else:
            return Severity.LOW