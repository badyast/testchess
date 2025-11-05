@echo off
REM Chess Engine Testing Framework - Web Interface Starter

echo ========================================
echo Chess Engine Testing Framework
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python ist nicht installiert oder nicht im PATH
    echo Bitte installieren Sie Python 3.8 oder neuer von python.org
    pause
    exit /b 1
)

echo Python gefunden!
echo.

REM Check if dependencies are installed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Installiere Abhaengigkeiten...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo FEHLER: Konnte Abhaengigkeiten nicht installieren
        pause
        exit /b 1
    )
)

echo Starte Web-Server...
echo.
echo Oeffnen Sie Ihren Browser und gehen Sie zu:
echo http://localhost:8000
echo.
echo Druecken Sie Strg+C zum Beenden
echo.

python backend\web_app.py

pause
