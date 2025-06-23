@echo off
setlocal enabledelayedexpansion

REM Determine Project Code Directory (where this script resides)
set "CODE_DIR=%~dp0"
REM Remove trailing backslash
if "%CODE_DIR:~-1%"=="\" set "CODE_DIR=%CODE_DIR:~0,-1%"

REM Define installation directories
set "INSTALL_DIR=%USERPROFILE%\WaterLevelsApp"
set "PYTHON_DIR=%INSTALL_DIR%\python"
set "VENV_DIR=%INSTALL_DIR%\venv"

echo Setting up Water Levels Monitoring application...
echo Installation directory: %INSTALL_DIR%

REM Create installation directory if it doesn't exist
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Define Python version and URLs
set "PYTHON_VERSION=3.11.6"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.6/python-3.11.6-embed-amd64.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

REM Download and install Python if not already installed
if not exist "%PYTHON_DIR%\python.exe" (
    echo Installing fresh Python for this application...
    
    REM Download Python
    echo Downloading Python %PYTHON_VERSION%...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%INSTALL_DIR%\python.zip'"
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to download Python.
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

REM Create virtual environment if missing
if not exist "%VENV_DIR%" (
    echo Creating virtual environment in "%VENV_DIR%"...
    "%PYTHON_DIR%\python.exe" -m virtualenv "%VENV_DIR%"
) else (
    echo Using existing virtual environment at %VENV_DIR%
)

REM Install dependencies
echo Installing dependencies...
call "%VENV_DIR%\Scripts\activate.bat"
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install core packages first
echo Installing core packages first...
python -m pip install numpy pandas matplotlib

REM Install Google API packages (critical for app functionality)
echo Installing Google API packages...
python -m pip install google-api-python-client google-auth-oauthlib --upgrade

REM Install PyQt packages
echo Installing PyQt packages...
python -m pip install PyQt5==5.15.10 PyQt5_sip==12.13.0 PyQtWebEngine==5.15.6

REM Try to install scipy with flexible version
echo Installing scipy...
python -m pip install scipy --upgrade

REM Install other important packages
echo Installing other important packages...
python -m pip install requests folium branca pillow psutil --upgrade

REM Now try to install remaining requirements
echo Installing remaining packages from Requirements.txt...
python -m pip install -r "%CODE_DIR%\Requirements.txt" --ignore-installed

REM Verify critical dependencies are installed
echo Verifying critical dependencies...

echo Checking pandas...
python -c "import pandas" || (
    echo Retrying pandas installation...
    python -m pip install pandas --upgrade
    python -c "import pandas" || echo CRITICAL: pandas installation failed!
)

echo Checking matplotlib...
python -c "import matplotlib" || (
    echo Retrying matplotlib installation...
    python -m pip install matplotlib --upgrade
    python -c "import matplotlib" || echo CRITICAL: matplotlib installation failed!
)

echo Checking Google API client...
python -c "import googleapiclient" || (
    echo Retrying Google API client installation...
    python -m pip install google-api-python-client --upgrade
    python -c "import googleapiclient" || echo CRITICAL: Google API client installation failed!
)

echo Checking psutil...
python -c "import psutil" || (
    echo Retrying psutil installation...
    python -m pip install psutil --upgrade
    python -c "import psutil" || echo CRITICAL: psutil installation failed!
)

REM Create normal launcher script (no console window)
set "LAUNCHER=%INSTALL_DIR%\water_levels_app.bat"
(
    echo @echo off
    echo cd /d "%CODE_DIR%"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo if not exist "%VENV_DIR%\Lib\site-packages\googleapiclient" ^(
    echo     echo Installing missing Google API packages. Please wait...
    echo     python -m pip install google-api-python-client google-auth-oauthlib --upgrade
    echo ^)
    echo if not exist "%VENV_DIR%\Lib\site-packages\pandas" ^(
    echo     echo Installing missing pandas package. Please wait...
    echo     python -m pip install pandas matplotlib scipy --upgrade
    echo ^)
    echo "%VENV_DIR%\Scripts\python.exe" "%CODE_DIR%\main.py"
) > "%LAUNCHER%"

REM Create debug launcher script (shows console and errors)
set "DEBUG_LAUNCHER=%INSTALL_DIR%\water_levels_app_debug.bat"
(
    echo @echo off
    echo cd /d "%CODE_DIR%"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo if not exist "%VENV_DIR%\Lib\site-packages\googleapiclient" ^(
    echo     echo Installing missing Google API packages. Please wait...
    echo     python -m pip install google-api-python-client google-auth-oauthlib --upgrade
    echo ^)
    echo if not exist "%VENV_DIR%\Lib\site-packages\pandas" ^(
    echo     echo Installing missing pandas package. Please wait...
    echo     python -m pip install pandas matplotlib scipy --upgrade
    echo ^)
    echo python "%CODE_DIR%\main.py"
    echo pause
) > "%DEBUG_LAUNCHER%"

REM Create visualizer launcher script
set "VISUALIZER_LAUNCHER=%INSTALL_DIR%\water_level_visualizer_app.bat"
(
    echo @echo off
    echo cd /d "%CODE_DIR%\tools\Visualizer"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo if not exist "%VENV_DIR%\Lib\site-packages\matplotlib" ^(
    echo     echo Installing missing matplotlib package. Please wait...
    echo     python -m pip install pandas matplotlib scipy --upgrade
    echo ^)
    echo python "%CODE_DIR%\tools\Visualizer\main.py"
    echo pause
) > "%VISUALIZER_LAUNCHER%"

REM Copy debug launcher to project folder
copy "%DEBUG_LAUNCHER%" "%CODE_DIR%\debug_launcher.bat" /Y > nul

echo.
echo Setup complete!
echo Launcher created at: %LAUNCHER%
echo Debug launcher created at: %DEBUG_LAUNCHER%
echo Visualizer launcher created at: %VISUALIZER_LAUNCHER%
echo.
echo For troubleshooting, use the debug launcher to see error messages.
echo.
echo You can copy these launchers to your desktop for easy access.
echo.
pause
endlocal 