# Location Sync AI Service

**Python FastAPI Microservice for AI/ML Features**

Provides AI-powered quality validation, anomaly detection, and conflict resolution prediction for the Location Sync Gateway.

---

## Features

### 1. Quality Scoring (`/api/v1/quality/score`)
Evaluates location data quality on a 0-100 scale with detailed breakdown:
- **Coordinates validation** (20 points) - Missing, null island, extreme locations
- **Address completeness** (20 points) - Street, city, postal code, country
- **Opening hours validation** (20 points) - Format and completeness
- **Keywords/metadata** (20 points) - Name, categories, description
- **Consistency check** (20 points) - Comparison with historical data

Returns severity level: CRITICAL (<40), HIGH (40-59), MEDIUM (60-79), LOW (≥80)

### 2. Anomaly Detection (`/api/v1/anomaly/detect`)
Detects suspicious patterns using Isolation Forest:
- Coordinate anomalies (null island, extreme moves)
- Missing critical fields
- Suspicious data patterns
- Quality degradation

Returns anomaly score (0-1), anomaly flag, reasons, and confidence

### 3. Resolution Prediction (`/api/v1/resolution/predict`)
Predicts conflict resolution outcomes:
- **AUTO_ACCEPT** - External value should be accepted
- **AUTO_REVERT** - Revert to Uberall value
- **FLAG_FOR_REVIEW** - Requires human decision

Considers field type, data source authority, quality score, and historical patterns

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Build image
docker build -t location-sync-ai-service .

# Run container
docker run -d -p 8081:8081 --name ai-service location-sync-ai-service

# Check logs
docker logs -f ai-service
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
uvicorn app.main:app --reload --port 8081
```

### Option 3: With Gateway (Docker Compose)

See parent directory's `docker-compose.yml` for running both services together.

---

## API Documentation

### Interactive Docs

Once running, visit:
- **Swagger UI**: http://localhost:8081/docs
- **ReDoc**: http://localhost:8081/redoc

### Example Requests

#### 1. Calculate Quality Score

```bash
curl -X POST "http://localhost:8081/api/v1/quality/score" \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot": {
      "locationId": 1001,
      "name": "Test Restaurant",
      "coordinates": {
        "latitude": -1.286389,
        "longitude": 36.817223
      },
      "address": {
        "street": "123 Test Street",
        "city": "Nairobi",
        "state": "Nairobi County",
        "postalCode": "00100",
        "country": "Kenya"
      },
      "phone": "+254712345678",
      "categories": ["Restaurant"],
      "website": "https://test.com",
      "description": "A great restaurant"
    }
  }'
```

**Response:**
```json
{
  "overallScore": 95,
  "breakdown": {
    "coordinates": 20,
    "address": 20,
    "openingHours": 0,
    "keywords": 20,
    "consistency": 20
  },
  "issues": [
    {
      "field": "openingHours",
      "issueType": "MISSING_REQUIRED_FIELD",
      "description": "Opening hours are missing",
      "severity": "MEDIUM"
    }
  ],
  "severity": "LOW"
}
```

#### 2. Detect Anomaly

```bash
curl -X POST "http://localhost:8081/api/v1/anomaly/detect" \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot": {
      "locationId": 1002,
      "name": "Test Location",
      "coordinates": {
        "latitude": 0,
        "longitude": 0
      }
    }
  }'
```

**Response:**
```json
{
  "anomalyScore": 0.9,
  "isAnomalous": true,
  "anomalyReasons": [
    "SUSPICIOUS_NULL_ISLAND: Coordinates are (0,0)"
  ],
  "confidence": 0.8
}
```

#### 3. Predict Resolution

```bash
curl -X POST "http://localhost:8081/api/v1/resolution/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "conflict": {
      "locationId": 1003,
      "fieldType": "PHONE",
      "source": "GOOGLE_MY_BUSINESS",
      "externalValue": "+254799999999",
      "uberallValue": "+254712345678",
      "qualityScore": 85,
      "anomalyScore": 0.2,
      "confidence": 0.9
    }
  }'
```

**Response:**
```json
{
  "predictedOutcome": "AUTO_REVERT",
  "confidence": 0.9,
  "reasoning": [
    "Phone numbers are centrally managed by HQ",
    "External phone changes are typically unauthorized"
  ],
  "mlScore": null
}
```

---

## Architecture

```
location-sync-ai-service/
├── app/
│   ├── main.py                  # FastAPI application
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   ├── services/
│   │   ├── quality_scorer.py    # Quality validation
│   │   ├── anomaly_detector.py  # Anomaly detection
│   │   └── resolution_predictor.py  # Resolution prediction
│   └── config/                  # Configuration
├── tests/                       # Unit tests
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image
└── README.md                    # This file
```

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI 0.109 |
| **Server** | Uvicorn (ASGI) |
| **Validation** | Pydantic 2.5 |
| **ML Library** | scikit-learn 1.4 |
| **Anomaly Detection** | PyOD (Isolation Forest) |
| **Monitoring** | Prometheus |
| **Testing** | pytest |

---

## Integration with Gateway

The Kotlin gateway calls this AI service via HTTP:

```kotlin
// In Kotlin Gateway
val aiServiceClient = HttpClient("http://ai-service:8081")

val qualityScore = aiServiceClient.post<QualityScore>(
    "/api/v1/quality/score",
    body = QualityScoreRequest(snapshot)
)

if (qualityScore.overallScore < 40) {
    // Reject low-quality data
    return ResolutionOutcome.AUTO_REVERT
}
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | 8081 |
| `LOG_LEVEL` | Logging level | INFO |
| `OPENAI_API_KEY` | OpenAI API key (optional) | - |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional) | - |

---

## Development

### Run Tests

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint code
ruff check app/ tests/

# Type checking
mypy app/
```

### Hot Reload

```bash
# Uvicorn with auto-reload
uvicorn app.main:app --reload --port 8081
```

---

## Monitoring

### Prometheus Metrics

Metrics exposed at `/metrics`:

```
http_requests_total
http_request_duration_seconds
quality_score_calculations_total
anomaly_detections_total
resolution_predictions_total
```

### Health Check

```bash
curl http://localhost:8081/health
```

**Response:**
```json
{
  "status": "UP",
  "version": "1.0.0",
  "models": {
    "quality_scorer": "rule-based",
    "anomaly_detector": "isolation-forest",
    "resolution_predictor": "rule-based"
  },
  "timestamp": "2026-09-23T15:30:00.000Z"
}
```

---

## Future Enhancements

### ML Model Training

Currently uses rule-based logic. Future versions will include:

1. **XGBoost Resolution Predictor**
   - Train on historical conflict decisions
   - Feature engineering (field type, source, quality, patterns)
   - Confidence scoring

2. **Advanced Anomaly Detection**
   - Train Isolation Forest on historical snapshots
   - Detect complex patterns and data drift
   - Model retraining pipeline

3. **LLM Explanations** (Optional)
   - GPT-4/Claude integration
   - Natural language explanations for conflicts
   - Cached responses for efficiency

### Training Pipeline

```bash
# Future endpoint (not yet implemented)
POST /api/v1/models/train/anomaly
POST /api/v1/models/train/resolution
```

---

## Production Deployment

### Docker Compose

```yaml
services:
  ai-service:
    build: ./location-sync-ai-service
    ports:
      - "8081:8081"
    environment:
      - LOG_LEVEL=INFO
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

### Kubernetes

See `k8s/` directory in parent project for deployment manifests.

---

## Support

- **Issues**: https://github.com/c-kiplimo/location-sync-ai-service/issues
- **Main Gateway**: https://github.com/c-kiplimo/Location-Sync-Gateway

---

**Version:** 1.0.0
**Python:** 3.11+
**License:** MIT