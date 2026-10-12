#!/bin/bash
# Quick development startup script for Python AI Service

set -e

echo "🤖 Starting Location Sync AI Service..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "🎯 Starting FastAPI server..."
echo "   Server: http://localhost:8081"
echo "   Swagger UI: http://localhost:8081/docs"
echo "   Health Check: http://localhost:8081/health"
echo ""

# Run server
uvicorn app.main:app --reload --port 8081