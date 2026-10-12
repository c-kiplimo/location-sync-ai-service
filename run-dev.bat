@echo off
REM Quick development startup script for Python AI Service

echo.
echo ================================
echo Location Sync AI Service
echo ================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo.
echo Starting FastAPI server...
echo   Server: http://localhost:8081
echo   Swagger UI: http://localhost:8081/docs
echo   Health Check: http://localhost:8081/health
echo.

REM Run server
uvicorn app.main:app --reload --port 8081