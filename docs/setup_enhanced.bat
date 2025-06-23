@echo off
setlocal enabledelayedexpansion

REM Enhanced Setup Script for Water Levels Monitoring Application
REM Includes auto-update system and improved directory structure

REM Determine Project Code Directory (where this script resides)
set "CODE_DIR=%~dp0"
REM Remove trailing backslash
if "%CODE_DIR:~-1%"=="\" set "CODE_DIR=%CODE_DIR:~0,-1%"

REM Define installation directories
set "INSTALL_DIR=%USERPROFILE%\WaterLevelsApp"
set "PYTHON_DIR=%INSTALL_DIR%\python"
set "VENV_DIR=%INSTALL_DIR%\venv"
set "APP_DIR=%INSTALL_DIR%\app"
set "BACKUP_DIR=%INSTALL_DIR%\backups"

echo ===============================================
echo Water Levels Monitoring Application Setup
echo Enhanced Installation with Auto-Update System
echo ===============================================
echo Installation directory: %INSTALL_DIR%
echo.

REM Create installation directory structure
echo Creating installation directories...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%APP_DIR%" mkdir "%APP_DIR%"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Define Python version and URLs
set "PYTHON_VERSION=3.11.6"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.6/python-3.11.6-embed-amd64.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

REM Download and install Python if not already installed
if not exist "%PYTHON_DIR%\python.exe" (
    echo Installing fresh Python %PYTHON_VERSION% for this application...
    
    REM Download Python
    echo Downloading Python %PYTHON_VERSION%...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%INSTALL_DIR%\python.zip'"
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to download Python.
        pause
        exit /b 1
    )
    
    REM Extract Python
    echo Extracting Python...
    powershell -Command "Expand-Archive -Path '%INSTALL_DIR%\python.zip' -DestinationPath '%PYTHON_DIR%' -Force"
    if exist "%INSTALL_DIR%\python.zip" del "%INSTALL_DIR%\python.zip"
    
    REM Enable site-packages by modifying python*._pth file
    echo Enabling site-packages...
    for %%F in ("%PYTHON_DIR%\python*._pth") do (
        type "%%F" > "%%F.temp"
        echo import site >> "%%F.temp"
        move /y "%%F.temp" "%%F"
    )
    
    REM Download and install pip
    echo Installing pip...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%GET_PIP_URL%' -OutFile '%INSTALL_DIR%\get-pip.py'"
    "%PYTHON_DIR%\python.exe" "%INSTALL_DIR%\get-pip.py" --no-warn-script-location
    if exist "%INSTALL_DIR%\get-pip.py" del "%INSTALL_DIR%\get-pip.py"
    
    echo Python installation complete.
) else (
    echo Using existing Python installation at %PYTHON_DIR%
)

REM Install setuptools and virtualenv
echo Installing virtualenv...
"%PYTHON_DIR%\python.exe" -m pip install --no-warn-script-location setuptools virtualenv

REM Remove existing virtual environment if it exists (for clean install)
if exist "%VENV_DIR%" (
    echo Removing existing virtual environment for clean install...
    rmdir /s /q "%VENV_DIR%"
)

REM Create new virtual environment
echo Creating virtual environment in "%VENV_DIR%"...
"%PYTHON_DIR%\python.exe" -m virtualenv "%VENV_DIR%"

REM Install dependencies
echo Installing dependencies...
call "%VENV_DIR%\Scripts\activate.bat"
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install core packages first
echo Installing core packages...
python -m pip install numpy pandas matplotlib

REM Install auto-update dependencies
echo Installing auto-update system dependencies...
python -m pip install requests packaging

REM Install Google API packages (critical for app functionality)
echo Installing Google API packages...
python -m pip install google-api-python-client google-auth-oauthlib --upgrade

REM Install PyQt packages
echo Installing PyQt packages...
python -m pip install PyQt5==5.15.10 PyQt5_sip==12.13.0 PyQtWebEngine==5.15.6

REM Install other important packages
echo Installing other important packages...
python -m pip install scipy folium branca pillow psutil --upgrade

REM Copy application files to installation directory
echo Copying application files...
xcopy "%CODE_DIR%\src" "%APP_DIR%\src\" /E /I /Y
xcopy "%CODE_DIR%\main.py" "%APP_DIR%\" /Y
xcopy "%CODE_DIR%\Requirements.txt" "%APP_DIR%\" /Y
if exist "%CODE_DIR%\config" xcopy "%CODE_DIR%\config" "%APP_DIR%\config\" /E /I /Y
if exist "%CODE_DIR%\tools" xcopy "%CODE_DIR%\tools" "%APP_DIR%\tools\" /E /I /Y

REM Create version.json file
echo Creating version file...
(
    echo {
    echo   "version": "1.0.0",
    echo   "release_date": "%DATE%",
    echo   "description": "Water Level Monitoring System - Initial Installation",
    echo   "github_repo": "benjaled/water_levels_monitoring_-for_external_edits-",
    echo   "auto_update": {
    echo     "enabled": true,
    echo     "check_on_startup": true,
    echo     "backup_count": 3
    echo   },
    echo   "installation_path": "%APP_DIR%"
    echo }
) > "%APP_DIR%\version.json"

REM Create enhanced launcher script with auto-update check
set "LAUNCHER=%INSTALL_DIR%\water_levels_app.bat"
(
    echo @echo off
    echo REM Water Levels Monitoring Application Launcher
    echo REM With Auto-Update Support
    echo.
    echo cd /d "%APP_DIR%"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo.
    echo REM Check for missing dependencies and install if needed
    echo if not exist "%VENV_DIR%\Lib\site-packages\googleapiclient" ^(
    echo     echo Installing missing Google API packages. Please wait...
    echo     python -m pip install google-api-python-client google-auth-oauthlib --upgrade
    echo ^)
    echo if not exist "%VENV_DIR%\Lib\site-packages\pandas" ^(
    echo     echo Installing missing pandas package. Please wait...
    echo     python -m pip install pandas matplotlib scipy --upgrade
    echo ^)
    echo if not exist "%VENV_DIR%\Lib\site-packages\requests" ^(
    echo     echo Installing missing requests package for auto-update. Please wait...
    echo     python -m pip install requests packaging --upgrade
    echo ^)
    echo.
    echo REM Run the application
    echo "%VENV_DIR%\Scripts\python.exe" "%APP_DIR%\main.py"
) > "%LAUNCHER%"

REM Create debug launcher script
set "DEBUG_LAUNCHER=%INSTALL_DIR%\water_levels_app_debug.bat"
(
    echo @echo off
    echo echo Water Levels Monitoring Application - Debug Mode
    echo echo =============================================
    echo cd /d "%APP_DIR%"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo.
    echo echo Python version:
    echo python --version
    echo echo.
    echo echo Checking critical dependencies...
    echo python -c "import pandas; print('pandas: OK')" 2^>^&1 ^|^| echo pandas: MISSING
    echo python -c "import matplotlib; print('matplotlib: OK')" 2^>^&1 ^|^| echo matplotlib: MISSING
    echo python -c "import PyQt5; print('PyQt5: OK')" 2^>^&1 ^|^| echo PyQt5: MISSING
    echo python -c "import requests; print('requests: OK')" 2^>^&1 ^|^| echo requests: MISSING
    echo python -c "import googleapiclient; print('Google API: OK')" 2^>^&1 ^|^| echo Google API: MISSING
    echo.
    echo echo Starting application...
    echo python "%APP_DIR%\main.py"
    echo.
    echo echo Application ended. Press any key to close...
    echo pause ^>nul
) > "%DEBUG_LAUNCHER%"

REM Create visualizer launcher script
set "VISUALIZER_LAUNCHER=%INSTALL_DIR%\water_level_visualizer_app.bat"
(
    echo @echo off
    echo cd /d "%APP_DIR%\tools\Visualizer"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo if not exist "%VENV_DIR%\Lib\site-packages\matplotlib" ^(
    echo     echo Installing missing matplotlib package. Please wait...
    echo     python -m pip install pandas matplotlib scipy --upgrade
    echo ^)
    echo python "%APP_DIR%\tools\Visualizer\main.py"
    echo pause
) > "%VISUALIZER_LAUNCHER%"

REM Create uninstaller script
set "UNINSTALLER=%INSTALL_DIR%\uninstall.bat"
(
    echo @echo off
    echo echo Water Levels Monitoring Application Uninstaller
    echo echo ===============================================
    echo echo.
    echo echo This will completely remove the Water Levels Monitoring application
    echo echo and all its data from your computer.
    echo echo.
    echo echo Installation directory: %INSTALL_DIR%
    echo echo.
    echo set /p confirm="Are you sure you want to uninstall? (y/N): "
    echo if /i "%%confirm%%" NEQ "y" (
    echo     echo Uninstall cancelled.
    echo     pause
    echo     exit /b 0
    echo ^)
    echo.
    echo echo Removing application files...
    echo cd /d "%USERPROFILE%"
    echo if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
    echo echo.
    echo echo Uninstall complete.
    echo pause
) > "%UNINSTALLER%"

echo.
echo ===============================================
echo Setup Complete!
echo ===============================================
echo.
echo Installation directory: %INSTALL_DIR%
echo Application files: %APP_DIR%
echo.
echo Launchers created:
echo   Main app: %LAUNCHER%
echo   Debug mode: %DEBUG_LAUNCHER%
echo   Visualizer: %VISUALIZER_LAUNCHER%
echo   Uninstaller: %UNINSTALLER%
echo.
echo Features included:
echo   ✓ Isolated Python environment
echo   ✓ All dependencies installed
echo   ✓ Auto-update system enabled
echo   ✓ Backup system for safe updates
echo   ✓ Debug mode for troubleshooting
echo   ✓ Easy uninstall option
echo.
echo You can copy the launchers to your desktop for easy access.
echo The application will automatically check for updates on startup.
echo.
echo For troubleshooting, use the debug launcher to see detailed error messages.
echo.
pause
endlocal