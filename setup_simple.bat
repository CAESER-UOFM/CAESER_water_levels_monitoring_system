@echo off
setlocal enabledelayedexpansion

REM ================================================================
REM CAESER Water Levels Monitoring Application - Simple Installer
REM ================================================================
REM This installer does NOT require administrator rights!
REM Everything installs to your user profile directory.
REM ================================================================

echo.
echo ===============================================
echo CAESER Water Levels Monitoring Application
echo Simple Installation (No Admin Required)
echo ===============================================
echo.

REM Determine Project Code Directory (where this script resides)
set "CODE_DIR=%~dp0"
REM Remove trailing backslash
if "%CODE_DIR:~-1%"=="\" set "CODE_DIR=%CODE_DIR:~0,-1%"

REM Default installation directory
set "INSTALL_DIR=%USERPROFILE%\WaterLevelsApp"

echo Default installation directory: %INSTALL_DIR%
echo.
set /p custom_path="Press Enter to use default, or type a custom path: "
if not "%custom_path%"=="" set "INSTALL_DIR=%custom_path%"

echo.
echo Installation directory: %INSTALL_DIR%
echo.

REM Ask about desktop shortcuts
set /p create_shortcuts="Create desktop shortcuts? (Y/n): "
if /i "%create_shortcuts%"=="n" (
    set "CREATE_DESKTOP=False"
) else (
    set "CREATE_DESKTOP=True"
)

REM Ask about source deletion
set /p delete_source="Delete source folder after installation? (Y/n): "
if /i "%delete_source%"=="n" (
    set "DELETE_SOURCE=False"
) else (
    set "DELETE_SOURCE=True"
)

echo.
echo Starting installation...
echo - Installation directory: %INSTALL_DIR%
echo - Create desktop shortcuts: %CREATE_DESKTOP%
echo - Delete source after install: %DELETE_SOURCE%
echo.
pause

REM Expand environment variables in path
call set "INSTALL_DIR=%INSTALL_DIR%"

REM Define installation subdirectories
set "PYTHON_DIR=%INSTALL_DIR%\python"
set "VENV_DIR=%INSTALL_DIR%\venv"
set "BACKUP_DIR=%INSTALL_DIR%\backups"

REM Create installation directory structure
echo Creating installation directories...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
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
xcopy "%CODE_DIR%\src" "%INSTALL_DIR%\src\" /E /I /Y
xcopy "%CODE_DIR%\main.py" "%INSTALL_DIR%\" /Y
xcopy "%CODE_DIR%\Requirements.txt" "%INSTALL_DIR%\" /Y
if exist "%CODE_DIR%\config" xcopy "%CODE_DIR%\config" "%INSTALL_DIR%\config\" /E /I /Y
if exist "%CODE_DIR%\tools" xcopy "%CODE_DIR%\tools" "%INSTALL_DIR%\tools\" /E /I /Y
if exist "%CODE_DIR%\assets" xcopy "%CODE_DIR%\assets" "%INSTALL_DIR%\assets\" /E /I /Y
if exist "%CODE_DIR%\Legacy_tables" xcopy "%CODE_DIR%\Legacy_tables" "%INSTALL_DIR%\Legacy_tables\" /E /I /Y

REM Create version.json file
echo Creating version file...
(
    echo {
    echo   "version": "1.0.0-beta",
    echo   "release_date": "%DATE%",
    echo   "description": "Water Level Monitoring System - Simple Installation",
    echo   "github_repo": "CAESER-UOFM/CAESER_water_levels_monitoring_system",
    echo   "auto_update": {
    echo     "enabled": true,
    echo     "check_on_startup": true,
    echo     "backup_count": 3
    echo   },
    echo   "installation_path": "%INSTALL_DIR%"
    echo }
) > "%INSTALL_DIR%\version.json"

REM Create launcher scripts
echo Creating launcher scripts...

REM Main launcher
set "LAUNCHER=%INSTALL_DIR%\water_levels_app.bat"
(
    echo @echo off
    echo cd /d "%INSTALL_DIR%"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo python "%INSTALL_DIR%\main.py"
) > "%LAUNCHER%"

REM Debug launcher
set "DEBUG_LAUNCHER=%INSTALL_DIR%\water_levels_app_debug.bat"
(
    echo @echo off
    echo echo CAESER Water Levels Monitoring - Debug Mode
    echo echo ==========================================
    echo cd /d "%INSTALL_DIR%"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo python "%INSTALL_DIR%\main.py"
    echo pause
) > "%DEBUG_LAUNCHER%"

REM Visualizer launcher
set "VISUALIZER_LAUNCHER=%INSTALL_DIR%\water_level_visualizer_app.bat"
(
    echo @echo off
    echo cd /d "%INSTALL_DIR%\tools\Visualizer"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo python "%INSTALL_DIR%\tools\Visualizer\main.py"
    echo pause
) > "%VISUALIZER_LAUNCHER%"

REM Create desktop shortcuts if requested
if "%CREATE_DESKTOP%"=="True" (
    echo Creating desktop shortcuts...
    
    REM Get desktop path - simple fallback method
    set "DESKTOP_PATH=%USERPROFILE%\Desktop"
    
    REM Create shortcuts using simple method
    echo Creating shortcuts on desktop...
    powershell -Command "& {$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP_PATH%\Water Levels Monitoring.lnk'); $Shortcut.TargetPath = '%LAUNCHER%'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'CAESER Water Levels Monitoring Application'; $Shortcut.Save()}"
    powershell -Command "& {$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP_PATH%\Water Levels Monitoring (Debug).lnk'); $Shortcut.TargetPath = '%DEBUG_LAUNCHER%'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'CAESER Water Levels Monitoring - Debug Mode'; $Shortcut.Save()}"
    
    echo Desktop shortcuts created successfully.
)

echo.
echo ===============================================
echo Setup Complete!
echo ===============================================
echo.
echo Installation directory: %INSTALL_DIR%
echo.
echo Launchers created:
echo   Main app: %LAUNCHER%
echo   Debug mode: %DEBUG_LAUNCHER%
echo   Visualizer: %VISUALIZER_LAUNCHER%

if "%CREATE_DESKTOP%"=="True" (
    echo.
    echo Desktop shortcuts created:
    echo   - Water Levels Monitoring
    echo   - Water Levels Monitoring (Debug)
)

echo.
echo You can now launch the application from:
if "%CREATE_DESKTOP%"=="True" (
    echo   - Desktop shortcuts
)
echo   - Installation directory: %INSTALL_DIR%
echo.

REM Handle source folder deletion if requested
if "%DELETE_SOURCE%"=="True" (
    echo.
    set /p final_confirm="Are you sure you want to delete the source folder? (y/N): "
    if /i "!final_confirm!"=="y" (
        echo Deleting source folder...
        cd /d "%USERPROFILE%"
        rmdir /s /q "%CODE_DIR%"
        echo Source folder deleted.
    )
)

echo.
echo Installation complete! Press any key to exit...
pause
endlocal