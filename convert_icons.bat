@echo off
echo Converting PNG icons to proper ICO format...
echo.

REM Run the PowerShell conversion script
powershell -ExecutionPolicy Bypass -File "%~dp0convert_icons.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Icon conversion completed successfully!
) else (
    echo.
    echo Warning: Icon conversion may have failed. Shortcuts will use system fallback icons.
)

pause