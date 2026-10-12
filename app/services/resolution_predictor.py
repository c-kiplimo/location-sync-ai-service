"""
Resolution Prediction Service

Predicts conflict resolution outcomes using ML (future: trained model)
Currently uses rule-based logic as foundation for ML training
"""
from typing import List, Dict, Any, Optional
from app.models.schemas import (
    ConflictData,
    ResolutionPredictionResponse,
    ResolutionOutcome,
    FieldType,
    DataSource
)


class ResolutionPredictor:
    """Predicts conflict resolution outcomes"""

    def __init__(self):
        """Initialize predictor with rule-based logic"""
        # In production, this would load a trained ML model
        # For now, we use expert rules as baseline
        self.model_loaded = False

    def predict_resolution(
        self,
        conflict: ConflictData,
        historical_decisions: Optional[List[Dict[str, Any]]] = None
    ) -> ResolutionPredictionResponse:
        """
        Predict resolution outcome for a conflict

        Args:
            conflict: Conflict data
            historical_decisions: Past decisions for learning (optional)

        Returns:
            Predicted outcome with confidence and reasoning
        """
        # Extract features
        features = self._extract_features(conflict)

        # Make prediction (currently rule-based, future: ML model)
        outcome, confidence, reasoning = self._predict_with_rules(
            conflict, features
        )

        # If we have historical data, adjust confidence
        if historical_decisions:
            confidence = self._adjust_confidence_with_history(
                outcome, conflict, historical_decisions, confidence
            )

        return ResolutionPredictionResponse(
            predictedOutcome=outcome,
            confidence=confidence,
            reasoning=reasoning,
            mlScore=None  # Would be populated by ML model
        )

    def _extract_features(self, conflict: ConflictData) -> Dict[str, Any]:
        """Extract features for ML prediction"""
        return {
            "field_type": conflict.fieldType.value,
            "source": conflict.source.value,
            "quality_score": conflict.qualityScore or 50,
            "anomaly_score": conflict.anomalyScore or 0.0,
            "base_confidence": conflict.confidence,
            "has_quality_issues": (conflict.qualityScore or 100) < 60,
            "is_critical_quality": (conflict.qualityScore or 100) < 40,
            "is_anomalous": (conflict.anomalyScore or 0) > 0.7
        }

    def _predict_with_rules(
        self,
        conflict: ConflictData,
        features: Dict[str, Any]
    ) -> tuple[ResolutionOutcome, float, List[str]]:
        """
        Rule-based prediction (foundation for ML model)

        Returns:
            (outcome, confidence, reasoning)
        """
        reasoning = []
        confidence = 0.8

        # Rule 1: Critical quality -> AUTO_REVERT
        if features["is_critical_quality"]:
            reasoning.append(
                f"Quality score is critical ({features['quality_score']}/100)"
            )
            reasoning.append("Rejecting low-quality data to protect system integrity")
            return ResolutionOutcome.AUTO_REVERT, 0.95, reasoning

        # Rule 2: High anomaly score -> FLAG_FOR_REVIEW
        if features["is_anomalous"]:
            reasoning.append(
                f"Anomaly score is high ({features['anomaly_score']:.2f})"
            )
            reasoning.append("Flagging suspicious data for human review")
            return ResolutionOutcome.FLAG_FOR_REVIEW, 0.85, reasoning

        # Rule 3: Field-specific rules based on source authority
        outcome, field_confidence, field_reasoning = self._apply_field_rules(
            conflict.fieldType, conflict.source, features["quality_score"]
        )
        reasoning.extend(field_reasoning)
        confidence = field_confidence

        return outcome, confidence, reasoning

    def _apply_field_rules(
        self,
        field_type: FieldType,
        source: DataSource,
        quality_score: int
    ) -> tuple[ResolutionOutcome, float, List[str]]:
        """Apply field-specific resolution rules"""
        reasoning = []

        # PHONE: HQ controls phone numbers
        if field_type == FieldType.PHONE:
            reasoning.append("Phone numbers are centrally managed by HQ")
            reasoning.append("External phone changes are typically unauthorized")
            return ResolutionOutcome.AUTO_REVERT, 0.9, reasoning

        # OPENING_HOURS: Franchisees control hours
        elif field_type == FieldType.OPENING_HOURS:
            if source == DataSource.GOOGLE_MY_BUSINESS:
                reasoning.append("Google My Business is authoritative for opening hours")
                reasoning.append("Local franchisees know their market best")
                if quality_score >= 70:
                    reasoning.append(f"Quality score is good ({quality_score}/100)")
                    return ResolutionOutcome.AUTO_ACCEPT, 0.85, reasoning
                else:
                    reasoning.append(f"Quality score is low ({quality_score}/100)")
                    return ResolutionOutcome.FLAG_FOR_REVIEW, 0.75, reasoning
            else:
                reasoning.append(f"Source {source.value} has lower authority for hours")
                return ResolutionOutcome.FLAG_FOR_REVIEW, 0.7, reasoning

        # CATEGORIES: Brand controls categories
        elif field_type == FieldType.CATEGORIES:
            reasoning.append("Categories are part of brand identity")
            reasoning.append("Unauthorized category changes can hurt SEO")
            return ResolutionOutcome.AUTO_REVERT, 0.9, reasoning

        # TEMPORARY_CLOSURE: Depends on source
        elif field_type == FieldType.TEMPORARY_CLOSURE:
            if source == DataSource.ERP_SYSTEM:
                reasoning.append("ERP system has authoritative work order data")
                reasoning.append("Planned closures should be published immediately")
                return ResolutionOutcome.AUTO_ACCEPT, 0.95, reasoning
            elif source == DataSource.POS_SYSTEM:
                reasoning.append("POS system detected potential closure from transaction data")
                reasoning.append("Requires human confirmation before publishing")
                return ResolutionOutcome.FLAG_FOR_REVIEW, 0.75, reasoning
            else:
                reasoning.append(f"Source {source.value} has uncertain closure authority")
                return ResolutionOutcome.FLAG_FOR_REVIEW, 0.7, reasoning

        # COORDINATES: Suspicious if moved
        elif field_type == FieldType.COORDINATES:
            reasoning.append("Coordinate changes are rare and suspicious")
            reasoning.append("Locations don't typically move")
            return ResolutionOutcome.FLAG_FOR_REVIEW, 0.8, reasoning

        # ADDRESS: Moderate authority
        elif field_type == FieldType.ADDRESS:
            if quality_score >= 80:
                reasoning.append(f"High quality address data ({quality_score}/100)")
                reasoning.append("Accepting well-formatted address update")
                return ResolutionOutcome.AUTO_ACCEPT, 0.75, reasoning
            else:
                reasoning.append(f"Low quality address data ({quality_score}/100)")
                return ResolutionOutcome.FLAG_FOR_REVIEW, 0.7, reasoning

        # WEBSITE: Moderate authority
        elif field_type == FieldType.WEBSITE:
            if source == DataSource.GOOGLE_MY_BUSINESS:
                reasoning.append("Google My Business is reasonable source for website")
                if quality_score >= 70:
                    return ResolutionOutcome.AUTO_ACCEPT, 0.75, reasoning
                else:
                    return ResolutionOutcome.FLAG_FOR_REVIEW, 0.7, reasoning
            else:
                return ResolutionOutcome.FLAG_FOR_REVIEW, 0.65, reasoning

        # DEFAULT: Flag for review
        else:
            reasoning.append(f"No specific rule for field type {field_type.value}")
            reasoning.append("Defaulting to manual review")
            return ResolutionOutcome.FLAG_FOR_REVIEW, 0.6, reasoning

    def _adjust_confidence_with_history(
        self,
        predicted_outcome: ResolutionOutcome,
        conflict: ConflictData,
        historical: List[Dict[str, Any]],
        base_confidence: float
    ) -> float:
        """
        Adjust confidence based on historical decisions

        In production, this would use the ML model's learned patterns
        """
        if not historical or len(historical) == 0:
            return base_confidence

        # Find similar historical conflicts
        similar = [
            h for h in historical
            if (h.get("fieldType") == conflict.fieldType.value and
                h.get("source") == conflict.source.value)
        ]

        if not similar:
            return base_confidence

        # Calculate historical outcome distribution
        outcome_counts = {}
        for h in similar:
            outcome = h.get("outcome", "UNKNOWN")
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        # If our prediction matches the majority historical outcome, increase confidence
        if predicted_outcome.value in outcome_counts:
            ratio = outcome_counts[predicted_outcome.value] / len(similar)
            if ratio > 0.7:
                # Strong historical pattern supports our prediction
                return min(base_confidence * 1.15, 0.95)
            elif ratio < 0.3:
                # Historical pattern contradicts our prediction
                return base_confidence * 0.85

        return base_confidence

    def train_model(self, training_data: List[Dict[str, Any]]):
        """
        Train ML model on historical decisions

        This is a placeholder for future ML model training
        In production, this would:
        1. Extract features from historical conflicts
        2. Train XGBoost or similar classifier
        3. Save trained model for inference
        4. Validate on held-out test set
        """
        # TODO: Implement ML training pipeline
        # For now, we rely on rule-based logic
        pass