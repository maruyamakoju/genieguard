@echo off
echo ============================================
echo GenieGuard: World-Sim CI - Demo
echo ============================================
echo.
echo This will:
echo   1. Randomly inject 1-3 bugs
echo   2. Detect bugs via telemetry
echo   3. Auto-repair using patch catalog
echo   4. Re-verify and generate report
echo.
echo Starting in 3 seconds...
timeout /t 3 >nul
echo.
python genieguard.py
echo.
echo ============================================
echo Demo complete! Check output/ for artifacts:
echo   - audit_report.json
echo   - patch.diff
echo   - before.png / after.png
echo   - ci_result.txt
echo ============================================
pause
