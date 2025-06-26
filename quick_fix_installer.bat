@echo off
echo ================================================================
echo              QUICK FIX - NO MORE EXPERIMENTS
echo ================================================================
echo.
echo Fixing the TWO core issues:
echo 1. App not launching properly
echo 2. Icons not showing
echo.

set "INSTALL_DIR=%USERPROFILE%\CAESER_Water_levels_monitoring_system"

if not exist "%INSTALL_DIR%" (
    echo ERROR: Installation directory not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

echo [FIX 1] Replacing VBScript with working batch launchers...

REM Create working batch launcher that ACTUALLY works
(
    echo @echo off
    echo cd /d "%INSTALL_DIR%"
    echo call "%INSTALL_DIR%\venv\Scripts\activate.bat"
    echo start /min "" "%INSTALL_DIR%\venv\Scripts\pythonw.exe" "%INSTALL_DIR%\main.py"
) > "%INSTALL_DIR%\launchers\water_levels_app_WORKING.bat"

echo   ✓ Created working batch launcher

echo [FIX 2] Creating shortcuts that point to WORKING batch files...

REM Delete broken shortcuts
del "%INSTALL_DIR%\CAESER Water Levels Monitoring.lnk" 2>nul
del "%INSTALL_DIR%\CAESER Water Level Visualizer.lnk" 2>nul

REM Create simple working shortcuts - NO ICONS for now, just WORKING
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%INSTALL_DIR%\CAESER Water Levels Monitoring.lnk'); $s.TargetPath = '%INSTALL_DIR%\launchers\water_levels_app_WORKING.bat'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Save()"

echo   ✓ Created working shortcut (no custom icon yet, but WORKS)

echo.
echo ================================================================
echo QUICK FIX COMPLETE
echo.
echo TEST THIS:
echo 1. Double-click: CAESER Water Levels Monitoring.lnk
echo 2. App should launch properly now
echo.
echo If this works, we can add icons later.
echo If this doesn't work, the problem is deeper.
echo ================================================================

start "" "%INSTALL_DIR%"
pause