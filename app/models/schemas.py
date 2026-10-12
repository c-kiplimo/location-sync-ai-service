"""
Pydantic models for request/response schemas
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class DataSource(str, Enum):
    """External data sources"""
    GOOGLE_MY_BUSINESS = "GOOGLE_MY_BUSINESS"
    POS_SYSTEM = "POS_SYSTEM"
    ERP_SYSTEM = "ERP_SYSTEM"
    WEBHOOK = "WEBHOOK"
    MANUAL = "MANUAL"


class FieldType(str, Enum):
    """Location field types"""
    PHONE = "PHONE"
    OPENING_HOURS = "OPENING_HOURS"
    COORDINATES = "COORDINATES"
    CATEGORIES = "CATEGORIES"
    ADDRESS = "ADDRESS"
    WEBSITE = "WEBSITE"
    DESCRIPTION = "DESCRIPTION"
    TEMPORARY_CLOSURE = "TEMPORARY_CLOSURE"


class Severity(str, Enum):
    """Quality issue severity levels"""
    CRITICAL = "CRITICAL"  # < 40
    HIGH = "HIGH"          # 40-59
    MEDIUM = "MEDIUM"      # 60-79
    LOW = "LOW"            # >= 80


class QualityIssueType(str, Enum):
    """Types of quality issues"""
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INCOMPLETE_DATA = "INCOMPLETE_DATA"
    INVALID_FORMAT = "INVALID_FORMAT"
    IMPLAUSIBLE_VALUE = "IMPLAUSIBLE_VALUE"
    INCONSISTENT_DATA = "INCONSISTENT_DATA"
    QUALITY_DEGRADATION = "QUALITY_DEGRADATION"


class ResolutionOutcome(str, Enum):
    """Conflict resolution outcomes"""
    AUTO_ACCEPT = "AUTO_ACCEPT"
    AUTO_REVERT = "AUTO_REVERT"
    FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW"


# Request/Response Models

class Coordinates(BaseModel):
    """Geographic coordinates"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class Address(BaseModel):
    """Location address"""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None


class TemporaryClosure(BaseModel):
    """Temporary closure information"""
    closed: bool
    reason: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None


class LocationSnapshot(BaseModel):
    """Location data snapshot"""
    locationId: int
    name: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    address: Optional[Address] = None
    phone: Optional[str] = None
    openingHours: Optional[Dict[str, Any]] = None
    categories: Optional[List[str]] = None
    website: Optional[str] = None
    description: Optional[str] = None
    temporaryClosure: Optional[TemporaryClosure] = None
    capturedAt: datetime = Field(default_factory=datetime.utcnow)


class QualityIssue(BaseModel):
    """Individual quality issue"""
    field: str
    issueType: QualityIssueType
    description: str
    severity: Severity


class QualityScoreRequest(BaseModel):
    """Request for quality scoring"""
    snapshot: LocationSnapshot
    historical: Optional[LocationSnapshot] = None  # For consistency check


class QualityScoreResponse(BaseModel):
    """Quality score result"""
    overallScore: int = Field(..., ge=0, le=100)
    breakdown: Dict[str, int] = Field(
        default_factory=lambda: {
            "coordinates": 0,
            "address": 0,
            "openingHours": 0,
            "keywords": 0,
            "consistency": 0
        }
    )
    issues: List[QualityIssue] = Field(default_factory=list)
    severity: Severity


class AnomalyDetectionRequest(BaseModel):
    """Request for anomaly detection"""
    snapshot: LocationSnapshot
    historical: Optional[List[LocationSnapshot]] = None


class AnomalyDetectionResponse(BaseModel):
    """Anomaly detection result"""
    anomalyScore: float = Field(..., ge=0, le=1)
    isAnomalous: bool
    anomalyReasons: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)


class ConflictData(BaseModel):
    """Conflict information for prediction"""
    locationId: int
    fieldType: FieldType
    source: DataSource
    externalValue: Any
    uberallValue: Any
    qualityScore: Optional[int] = None
    anomalyScore: Optional[float] = None
    confidence: float


class ResolutionPredictionRequest(BaseModel):
    """Request for resolution prediction"""
    conflict: ConflictData
    historicalDecisions: Optional[List[Dict[str, Any]]] = None


class ResolutionPredictionResponse(BaseModel):
    """Resolution prediction result"""
    predictedOutcome: ResolutionOutcome
    confidence: float = Field(..., ge=0, le=1)
    reasoning: List[str] = Field(default_factory=list)
    mlScore: Optional[float] = None


class ExplanationRequest(BaseModel):
    """Request for LLM explanation"""
    conflict: ConflictData
    qualityScore: Optional[QualityScoreResponse] = None
    anomalyScore: Optional[float] = None
    predictedOutcome: Optional[ResolutionOutcome] = None


class ExplanationResponse(BaseModel):
    """LLM-generated explanation"""
    summary: str
    reasoning: List[str]
    recommendation: str
    confidence: float


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    models: Dict[str, str]
    timestamp: datetime