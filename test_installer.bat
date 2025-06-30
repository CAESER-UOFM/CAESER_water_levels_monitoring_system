@echo off
echo ========================================
echo MINIMAL INSTALLER TEST
echo ========================================
echo.
echo [1] Testing basic variables...
set "DEFAULT_PATH=%USERPROFILE%\CAESER_Water_levels_monitoring_system"
echo DEFAULT_PATH: %DEFAULT_PATH%
echo USERPROFILE: %USERPROFILE%
echo TEMP: %TEMP%
echo.
pause

echo [2] Testing directory creation...
if exist "%DEFAULT_PATH%" (
    echo Directory already exists, removing...
    rmdir /s /q "%DEFAULT_PATH%" 2>nul
)
mkdir "%DEFAULT_PATH%"
if exist "%DEFAULT_PATH%" (
    echo SUCCESS: Directory created
) else (
    echo FAILED: Could not create directory
    pause
    exit /b 1
)
echo.
pause

echo [3] Testing Python download...
echo Downloading to: %DEFAULT_PATH%\python.zip
bitsadmin /transfer "PythonTest" "https://www.python.org/ftp/python/3.11.6/python-3.11.6-embed-amd64.zip" "%DEFAULT_PATH%\python.zip"
echo Download exit code: %ERRORLEVEL%
if exist "%DEFAULT_PATH%\python.zip" (
    echo SUCCESS: Python.zip downloaded
    dir "%DEFAULT_PATH%\python.zip"
) else (
    echo FAILED: Python.zip not found
)
echo.
pause

echo [4] Testing PowerShell extraction...
if exist "%DEFAULT_PATH%\python.zip" (
    mkdir "%DEFAULT_PATH%\python"
    powershell -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%DEFAULT_PATH%\python.zip' -DestinationPath '%DEFAULT_PATH%\python' -Force"
    echo Extraction exit code: %ERRORLEVEL%
    if exist "%DEFAULT_PATH%\python\python.exe" (
        echo SUCCESS: Python extracted
    ) else (
        echo FAILED: Python.exe not found after extraction
    )
) else (
    echo SKIPPED: No python.zip to extract
)
echo.
pause

echo [5] Test complete!
echo Check the folder: %DEFAULT_PATH%
start "" "%DEFAULT_PATH%"
pause