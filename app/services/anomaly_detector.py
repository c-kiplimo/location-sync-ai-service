"""
Anomaly Detection Service

Uses Isolation Forest to detect suspicious location data patterns
"""
import numpy as np
from typing import List, Optional
from sklearn.ensemble import IsolationForest
from app.models.schemas import (
    LocationSnapshot,
    AnomalyDetectionResponse
)


class AnomalyDetector:
    """Detects anomalies in location snapshots using Isolation Forest"""

    def __init__(self, contamination: float = 0.1):
        """
        Initialize anomaly detector

        Args:
            contamination: Expected proportion of outliers (default 10%)
        """
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.is_trained = False

    def detect_anomaly(
        self,
        snapshot: LocationSnapshot,
        historical: Optional[List[LocationSnapshot]] = None
    ) -> AnomalyDetectionResponse:
        """
        Detect if a snapshot is anomalous

        Args:
            snapshot: Current snapshot to check
            historical: Historical snapshots for training (optional)

        Returns:
            Anomaly detection result
        """
        # Extract features from snapshot
        features = self._extract_features(snapshot)

        # If we have historical data, train model
        if historical and len(historical) >= 10:
            self._train_on_historical(historical)

        # Calculate anomaly score
        if self.is_trained:
            # Use trained model
            anomaly_score = self._calculate_anomaly_score(features)
            is_anomalous = anomaly_score > 0.5
        else:
            # Use rule-based detection
            anomaly_score, is_anomalous = self._rule_based_detection(snapshot)

        # Identify reasons for anomaly
        reasons = self._identify_anomaly_reasons(snapshot, anomaly_score)

        # Calculate confidence
        confidence = min(abs(anomaly_score - 0.5) * 2, 1.0)

        return AnomalyDetectionResponse(
            anomalyScore=anomaly_score,
            isAnomalous=is_anomalous,
            anomalyReasons=reasons,
            confidence=confidence
        )

    def _extract_features(self, snapshot: LocationSnapshot) -> np.ndarray:
        """Extract numerical features from snapshot"""
        features = []

        # Coordinate features
        if snapshot.coordinates:
            features.extend([
                snapshot.coordinates.latitude,
                snapshot.coordinates.longitude,
                abs(snapshot.coordinates.latitude),  # Distance from equator
                abs(snapshot.coordinates.longitude)  # Distance from prime meridian
            ])
        else:
            features.extend([0, 0, 0, 0])

        # Completeness features
        features.append(1 if snapshot.name else 0)
        features.append(1 if snapshot.address else 0)
        features.append(1 if snapshot.phone else 0)
        features.append(1 if snapshot.openingHours else 0)
        features.append(len(snapshot.categories) if snapshot.categories else 0)
        features.append(1 if snapshot.website else 0)
        features.append(len(snapshot.description) if snapshot.description else 0)

        # Address completeness
        if snapshot.address:
            features.append(1 if snapshot.address.street else 0)
            features.append(1 if snapshot.address.city else 0)
            features.append(1 if snapshot.address.country else 0)
        else:
            features.extend([0, 0, 0])

        return np.array(features).reshape(1, -1)

    def _train_on_historical(self, historical: List[LocationSnapshot]):
        """Train model on historical data"""
        if len(historical) < 10:
            return

        # Extract features from all historical snapshots
        feature_matrix = []
        for snapshot in historical:
            features = self._extract_features(snapshot)
            feature_matrix.append(features.flatten())

        X = np.array(feature_matrix)

        # Train Isolation Forest
        self.model.fit(X)
        self.is_trained = True

    def _calculate_anomaly_score(self, features: np.ndarray) -> float:
        """Calculate anomaly score using trained model"""
        # Get anomaly score (-1 for outliers, 1 for inliers)
        score = self.model.score_samples(features)[0]

        # Convert to 0-1 scale (higher = more anomalous)
        # score_samples returns values roughly between -0.5 and 0.5
        # Normalize to 0-1 range
        normalized_score = 1 - ((score + 0.5) / 1.0)
        return max(0, min(1, normalized_score))

    def _rule_based_detection(
        self,
        snapshot: LocationSnapshot
    ) -> tuple[float, bool]:
        """
        Rule-based anomaly detection when no historical data available

        Returns:
            (anomaly_score, is_anomalous)
        """
        anomaly_indicators = []

        # Check for null island
        if snapshot.coordinates:
            if (snapshot.coordinates.latitude == 0 and
                snapshot.coordinates.longitude == 0):
                anomaly_indicators.append(0.9)

        # Check for extreme coordinates
        if snapshot.coordinates:
            if abs(snapshot.coordinates.latitude) > 85:
                anomaly_indicators.append(0.7)

        # Check for missing critical fields
        missing_critical = 0
        if not snapshot.name:
            missing_critical += 1
        if not snapshot.coordinates:
            missing_critical += 1
        if not snapshot.address:
            missing_critical += 1

        if missing_critical >= 2:
            anomaly_indicators.append(0.8)
        elif missing_critical == 1:
            anomaly_indicators.append(0.4)

        # Check for suspicious patterns
        if snapshot.phone and len(snapshot.phone) < 8:
            anomaly_indicators.append(0.3)

        if snapshot.name and len(snapshot.name) < 2:
            anomaly_indicators.append(0.5)

        # Calculate overall score
        if anomaly_indicators:
            anomaly_score = max(anomaly_indicators)
        else:
            anomaly_score = 0.1  # Low baseline

        is_anomalous = anomaly_score > 0.5

        return anomaly_score, is_anomalous

    def _identify_anomaly_reasons(
        self,
        snapshot: LocationSnapshot,
        anomaly_score: float
    ) -> List[str]:
        """Identify specific reasons for anomaly"""
        reasons = []

        if anomaly_score < 0.3:
            return reasons

        # Check specific anomaly patterns
        if snapshot.coordinates:
            if (snapshot.coordinates.latitude == 0 and
                snapshot.coordinates.longitude == 0):
                reasons.append("SUSPICIOUS_NULL_ISLAND: Coordinates are (0,0)")

            if abs(snapshot.coordinates.latitude) > 85:
                reasons.append("EXTREME_COORDINATES: Location near poles")

        # Missing critical data
        missing_fields = []
        if not snapshot.name:
            missing_fields.append("name")
        if not snapshot.coordinates:
            missing_fields.append("coordinates")
        if not snapshot.address:
            missing_fields.append("address")

        if len(missing_fields) >= 2:
            reasons.append(f"MISSING_CRITICAL_FIELDS: {', '.join(missing_fields)}")

        # Data quality issues
        if snapshot.phone and len(snapshot.phone) < 8:
            reasons.append("SUSPICIOUS_PHONE: Phone number too short")

        if snapshot.name and len(snapshot.name) < 2:
            reasons.append("SUSPICIOUS_NAME: Name too short")

        # Completeness score
        completeness = self._calculate_completeness(snapshot)
        if completeness < 0.4:
            reasons.append(f"LOW_COMPLETENESS: Only {completeness*100:.0f}% complete")

        return reasons

    def _calculate_completeness(self, snapshot: LocationSnapshot) -> float:
        """Calculate data completeness ratio"""
        total_fields = 10
        filled_fields = 0

        if snapshot.name:
            filled_fields += 1
        if snapshot.coordinates:
            filled_fields += 1
        if snapshot.address:
            filled_fields += 1
        if snapshot.phone:
            filled_fields += 1
        if snapshot.openingHours:
            filled_fields += 1
        if snapshot.categories:
            filled_fields += 1
        if snapshot.website:
            filled_fields += 1
        if snapshot.description:
            filled_fields += 1
        if snapshot.address and snapshot.address.city:
            filled_fields += 1
        if snapshot.address and snapshot.address.country:
            filled_fields += 1

        return filled_fields / total_fields