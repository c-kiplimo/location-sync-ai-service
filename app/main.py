"""
Location Sync AI Service - FastAPI Application

Provides AI/ML capabilities for location data quality and conflict resolution
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from datetime import datetime
import logging

from app.models.schemas import (
    QualityScoreRequest,
    QualityScoreResponse,
    AnomalyDetectionRequest,
    AnomalyDetectionResponse,
    ResolutionPredictionRequest,
    ResolutionPredictionResponse,
    HealthResponse
)
from app.services.quality_scorer import QualityScorer
from app.services.anomaly_detector import AnomalyDetector
from app.services.resolution_predictor import ResolutionPredictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Location Sync AI Service",
    description="AI/ML microservice for location data quality validation and conflict resolution",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Initialize AI services
quality_scorer = QualityScorer()
anomaly_detector = AnomalyDetector(contamination=0.1)
resolution_predictor = ResolutionPredictor()

logger.info("Location Sync AI Service initialized successfully")


# Health and Status Endpoints

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="UP",
        version="1.0.0",
        models={
            "quality_scorer": "rule-based",
            "anomaly_detector": "isolation-forest" if anomaly_detector.is_trained else "rule-based",
            "resolution_predictor": "rule-based"
        },
        timestamp=datetime.utcnow()
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Location Sync AI Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "quality_score": "/api/v1/quality/score",
            "anomaly_detection": "/api/v1/anomaly/detect",
            "resolution_prediction": "/api/v1/resolution/predict"
        }
    }


# Quality Scoring Endpoints

@app.post("/api/v1/quality/score", response_model=QualityScoreResponse)
async def calculate_quality_score(request: QualityScoreRequest):
    """
    Calculate quality score for a location snapshot

    Evaluates data quality on a 0-100 scale with detailed breakdown:
    - Coordinates validation (20 points)
    - Address completeness (20 points)
    - Opening hours validation (20 points)
    - Keywords/metadata (20 points)
    - Consistency with historical data (20 points)

    Returns issues list and severity level (CRITICAL, HIGH, MEDIUM, LOW)
    """
    try:
        logger.info(f"Calculating quality score for location {request.snapshot.locationId}")

        result = quality_scorer.calculate_quality_score(
            snapshot=request.snapshot,
            historical=request.historical
        )

        logger.info(
            f"Quality score for location {request.snapshot.locationId}: "
            f"{result.overallScore}/100 ({result.severity.value})"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating quality score: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quality scoring failed: {str(e)}")


# Anomaly Detection Endpoints

@app.post("/api/v1/anomaly/detect", response_model=AnomalyDetectionResponse)
async def detect_anomaly(request: AnomalyDetectionRequest):
    """
    Detect anomalies in location snapshot

    Uses Isolation Forest algorithm to identify suspicious patterns:
    - Coordinate anomalies (null island, extreme locations)
    - Missing critical fields
    - Suspicious data patterns
    - Consistency violations

    Returns anomaly score (0-1), anomaly flag, reasons, and confidence
    """
    try:
        logger.info(f"Detecting anomalies for location {request.snapshot.locationId}")

        result = anomaly_detector.detect_anomaly(
            snapshot=request.snapshot,
            historical=request.historical
        )

        logger.info(
            f"Anomaly detection for location {request.snapshot.locationId}: "
            f"score={result.anomalyScore:.3f}, anomalous={result.isAnomalous}"
        )

        return result

    except Exception as e:
        logger.error(f"Error detecting anomaly: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(e)}")


# Resolution Prediction Endpoints

@app.post("/api/v1/resolution/predict", response_model=ResolutionPredictionResponse)
async def predict_resolution(request: ResolutionPredictionRequest):
    """
    Predict conflict resolution outcome

    Uses rule-based logic (foundation for future ML model) to predict:
    - AUTO_ACCEPT: External value should be accepted
    - AUTO_REVERT: Revert to Uberall value
    - FLAG_FOR_REVIEW: Requires human decision

    Considers:
    - Field type and data source authority
    - Quality score
    - Anomaly score
    - Historical decision patterns

    Returns predicted outcome, confidence, and reasoning
    """
    try:
        logger.info(
            f"Predicting resolution for conflict: location={request.conflict.locationId}, "
            f"field={request.conflict.fieldType.value}, source={request.conflict.source.value}"
        )

        result = resolution_predictor.predict_resolution(
            conflict=request.conflict,
            historical_decisions=request.historicalDecisions
        )

        logger.info(
            f"Resolution prediction for location {request.conflict.locationId}: "
            f"{result.predictedOutcome.value} (confidence={result.confidence:.2f})"
        )

        return result

    except Exception as e:
        logger.error(f"Error predicting resolution: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resolution prediction failed: {str(e)}")


# Model Management Endpoints (for future ML training)

@app.post("/api/v1/models/train/anomaly")
async def train_anomaly_model(training_data: list):
    """
    Train anomaly detection model on historical data

    Future endpoint for ML model training
    """
    return {
        "status": "not_implemented",
        "message": "ML training pipeline not yet implemented",
        "current_mode": "rule-based"
    }


@app.post("/api/v1/models/train/resolution")
async def train_resolution_model(training_data: list):
    """
    Train resolution prediction model on historical decisions

    Future endpoint for ML model training
    """
    return {
        "status": "not_implemented",
        "message": "ML training pipeline not yet implemented",
        "current_mode": "rule-based"
    }


# Startup and Shutdown Events

@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("=" * 60)
    logger.info("Location Sync AI Service Starting")
    logger.info("=" * 60)
    logger.info("Services initialized:")
    logger.info("  - Quality Scorer: Ready")
    logger.info("  - Anomaly Detector: Ready")
    logger.info("  - Resolution Predictor: Ready")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("Location Sync AI Service shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info"
    )