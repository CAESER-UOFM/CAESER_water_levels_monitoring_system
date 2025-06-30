@echo off
setlocal enabledelayedexpansion

echo ===============================================================================
echo                    CAESER Water Levels Monitoring - Simple Setup
echo ===============================================================================
echo.

REM Use default installation directory
set "INSTALL_DIR=%USERPROFILE%\CAESER_Water_levels_monitoring_system"

echo Installation directory: %INSTALL_DIR%
echo.
echo Starting installation in 3 seconds...
timeout /t 3 /nobreak >nul

REM Clean up existing installation
if exist "%INSTALL_DIR%" (
    echo Removing existing installation...
    rmdir /s /q "%INSTALL_DIR%" 2>nul
)

REM Create directories
echo [1/7] Creating directories...
mkdir "%INSTALL_DIR%"
mkdir "%INSTALL_DIR%\python"
mkdir "%INSTALL_DIR%\venv"
mkdir "%INSTALL_DIR%\databases"
mkdir "%INSTALL_DIR%\databases\temp"

REM Download Python
echo [2/7] Downloading Python...
bitsadmin /transfer "PythonDownload" "https://www.python.org/ftp/python/3.11.6/python-3.11.6-embed-amd64.zip" "%INSTALL_DIR%\python.zip" >nul

REM Extract Python
echo [3/7] Extracting Python...
powershell -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%INSTALL_DIR%\python.zip' -DestinationPath '%INSTALL_DIR%\python' -Force" >nul
del "%INSTALL_DIR%\python.zip"

REM Enable site-packages
echo [4/7] Configuring Python...
for %%F in ("%INSTALL_DIR%\python\python*._pth") do (
    type "%%F" > "%%F.temp"
    echo import site >> "%%F.temp"
    move /y "%%F.temp" "%%F" >nul
)

REM Install pip
bitsadmin /transfer "PipDownload" "https://bootstrap.pypa.io/get-pip.py" "%INSTALL_DIR%\get-pip.py" >nul
"%INSTALL_DIR%\python\python.exe" "%INSTALL_DIR%\get-pip.py" --no-warn-script-location >nul
del "%INSTALL_DIR%\get-pip.py"

REM Install virtualenv
"%INSTALL_DIR%\python\python.exe" -m pip install --no-warn-script-location setuptools virtualenv >nul

REM Create virtual environment  
echo [5/7] Creating virtual environment...
"%INSTALL_DIR%\python\python.exe" -m virtualenv "%INSTALL_DIR%\venv" >nul

REM Install dependencies
echo [6/7] Installing dependencies (this may take a few minutes)...
call "%INSTALL_DIR%\venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
python -m pip install numpy pandas matplotlib requests packaging >nul
python -m pip install google-api-python-client google-auth-oauthlib >nul
python -m pip install PyQt5==5.15.10 PyQt5_sip==12.13.0 PyQtWebEngine==5.15.6 >nul
python -m pip install scipy folium branca pillow psutil >nul

REM Copy application files
echo [7/7] Copying application files...
set "CODE_DIR=%~dp0"
if "%CODE_DIR:~-1%"=="\" set "CODE_DIR=%CODE_DIR:~0,-1%"

xcopy "%CODE_DIR%\src" "%INSTALL_DIR%\src\" /E /I /Y >nul
xcopy "%CODE_DIR%\main.py" "%INSTALL_DIR%\" /Y >nul
xcopy "%CODE_DIR%\Requirements.txt" "%INSTALL_DIR%\" /Y >nul

if exist "%CODE_DIR%\config" xcopy "%CODE_DIR%\config" "%INSTALL_DIR%\config\" /E /I /Y >nul
if exist "%CODE_DIR%\tools" xcopy "%CODE_DIR%\tools" "%INSTALL_DIR%\tools\" /E /I /Y >nul
if exist "%CODE_DIR%\assets" xcopy "%CODE_DIR%\assets" "%INSTALL_DIR%\assets\" /E /I /Y >nul

REM Create launchers
(
    echo @echo off
    echo cd /d "%INSTALL_DIR%"
    echo call "%INSTALL_DIR%\venv\Scripts\activate.bat"
    echo python "%INSTALL_DIR%\main.py"
) > "%INSTALL_DIR%\water_levels_app.bat"

(
    echo @echo off
    echo echo CAESER Water Levels Monitoring - Debug Mode
    echo cd /d "%INSTALL_DIR%"
    echo call "%INSTALL_DIR%\venv\Scripts\activate.bat"
    echo python "%INSTALL_DIR%\main.py"
    echo pause
) > "%INSTALL_DIR%\water_levels_app_debug.bat"

echo.
echo ===============================================================================
echo                           INSTALLATION COMPLETE!
echo ===============================================================================
echo.
echo Installation directory: %INSTALL_DIR%
echo.
echo To run the application:
echo   - Double-click: water_levels_app.bat
echo   - For debugging: water_levels_app_debug.bat
echo.
echo Opening installation folder...
start "" "%INSTALL_DIR%"
echo.
pause