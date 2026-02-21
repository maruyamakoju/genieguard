@echo off
echo ============================================
echo GenieGuard Development Server
echo ============================================
echo.
echo Starting server at http://localhost:8080
echo.
echo   Simulator:  http://localhost:8080/index.html
echo   Dashboard:  http://localhost:8080/dashboard.html
echo.
echo Press Ctrl+C to stop.
echo ============================================
python server.py --no-open
