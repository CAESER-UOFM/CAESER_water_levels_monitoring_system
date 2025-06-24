@echo off
echo ============================================
echo CAESER Water Levels Monitoring - Debug Mode
echo ============================================
echo.

echo Step 1: Checking PowerShell availability...
powershell -Command "Write-Host 'PowerShell is working'"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PowerShell is not available or blocked
    echo This is likely a corporate security policy issue.
    pause
    exit /b 1
)

echo Step 2: Checking execution policy...
powershell -Command "Get-ExecutionPolicy"

echo Step 3: Testing Windows Forms...
powershell -Command "Add-Type -AssemblyName System.Windows.Forms; Write-Host 'Windows Forms available'"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Windows Forms not available
    pause
    exit /b 1
)

echo.
echo All preliminary checks passed!
echo.
echo Now attempting to run the main installer...
echo If this fails, we'll know the issue is in the GUI dialog.
echo.
pause

REM Try to run the original installer
call setup.bat

echo.
echo Installation attempt completed.
echo If you see this message, the installer ran without crashing.
pause