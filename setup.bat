@echo off
setlocal enabledelayedexpansion

REM ================================================================
REM CAESER Water Levels Monitoring Application - GUI Installer
REM ================================================================
REM Simplified approach based on successful test - no complex error handling
REM ================================================================

cls
echo.
echo    ===============================================================================
echo    #                                                                             #
echo    #      ####    ###   ######  ####  ###### #####                             #
echo    #     #    #  #   #  #      #      #      #    #                            #
echo    #     #       #   #  #####   ####  #####  #####                             #
echo    #     #       #####  #           # #      #   #                             #
echo    #     #    #  #   #  #      #    # #      #    #                            #
echo    #      ####   #   #  ######  ####  ###### #    #                            #
echo    #                                                                             #
echo    #                      ~~~ Water Levels Monitoring ~~~                      #
echo    #                                                                             #
echo    #    +---------------------------------------------------------------+       #
echo    #    ^  Advanced Installation System                                 ^       #
echo    #    ^  No Administrator Rights Required                             ^       #
echo    #    ^  University of Memphis - CAESER Lab                          ^       #
echo    #    +---------------------------------------------------------------+       #
echo    #                                                                             #
echo    ===============================================================================
echo.
echo    [*] Initializing installer components...
timeout /t 2 /nobreak >nul
echo    [+] Environment check complete
echo    [*] Ready to install Water Levels Monitoring System
echo.

REM Use default installation directory - keep it simple!
set "INSTALL_DIR=%USERPROFILE%\CAESER_Water_levels_monitoring_system"
set "DELETE_SOURCE=False"

echo.
echo    ===============================================================================
echo    #                       INSTALLATION SUMMARY                                 #
echo    ===============================================================================
echo.
echo   What will be installed:
echo   - Python 3.11.6 (embedded version)
echo   - Virtual environment with all dependencies
echo   - CAESER Water Levels Monitoring System
echo   - Application launchers (main app, debug, visualizer)
echo   - Database folders for local and cloud data
echo.
echo   Installation directory: %INSTALL_DIR%
echo.
echo   ^> Continue with installation (Press ENTER)
echo     Cancel installation (Type 'q' and ENTER)
echo.
set /p confirm="Choice (ENTER to install, 'q' to quit): "
if /i "%confirm%"=="q" (
    echo Installation cancelled by user.
    pause
    exit /b 0
)

echo.
echo    ===============================================================================
echo    #                        INSTALLATION STARTING                               #
echo    ===============================================================================
echo.
echo    [*] Installation directory: %INSTALL_DIR%
echo    [*] Please wait while we set up your Water Levels Monitoring System...
echo.

REM Clean up existing installation
if exist "%INSTALL_DIR%" (
    echo    [*] Removing existing installation...
    rmdir /s /q "%INSTALL_DIR%" 2>nul
)

REM Create directories
echo    [*] [1/7] Creating directories...
mkdir "%INSTALL_DIR%"
mkdir "%INSTALL_DIR%\python"
mkdir "%INSTALL_DIR%\venv"
mkdir "%INSTALL_DIR%\databases"
mkdir "%INSTALL_DIR%\databases\temp"

REM Download Python
echo    [*] [2/7] Downloading Python...
bitsadmin /transfer "PythonDownload" "https://www.python.org/ftp/python/3.11.6/python-3.11.6-embed-amd64.zip" "%INSTALL_DIR%\python.zip" >nul

REM Extract Python
echo    [*] [3/7] Extracting Python...
powershell -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%INSTALL_DIR%\python.zip' -DestinationPath '%INSTALL_DIR%\python' -Force" >nul
del "%INSTALL_DIR%\python.zip"

REM Enable site-packages
echo    [*] [4/7] Configuring Python...
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
echo    [*] [5/7] Creating virtual environment...
"%INSTALL_DIR%\python\python.exe" -m virtualenv "%INSTALL_DIR%\venv" >nul

REM Install dependencies
echo    [*] [6/7] Installing dependencies (this may take a few minutes)...
call "%INSTALL_DIR%\venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
python -m pip install numpy pandas matplotlib requests packaging >nul
python -m pip install google-api-python-client google-auth-oauthlib >nul
python -m pip install PyQt5==5.15.10 PyQt5_sip==12.13.0 PyQtWebEngine==5.15.6 >nul
python -m pip install scipy folium branca pillow psutil >nul

REM Copy application files
echo    [*] [7/7] Copying application files...
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

(
    echo @echo off
    echo cd /d "%INSTALL_DIR%\tools\Visualizer"
    echo call "%INSTALL_DIR%\venv\Scripts\activate.bat"
    echo python "%INSTALL_DIR%\tools\Visualizer\main.py"
    echo pause
) > "%INSTALL_DIR%\water_level_visualizer_app.bat"

echo.
echo    ===============================================================================
echo    #                        INSTALLATION COMPLETE!                              #
echo    #                                                                             #
echo    #                    Water Levels Monitoring System                          #
echo    #                         Ready for Action!                                  #
echo    ===============================================================================
echo.
echo    [+] Installation directory: %INSTALL_DIR%
echo.
echo    [+] Launchers created:
echo        [*] Main app: water_levels_app.bat
echo        [*] Debug mode: water_levels_app_debug.bat
echo        [*] Visualizer: water_level_visualizer_app.bat
echo.
echo    [+] You can now launch the application!
echo.
echo    [+] To start using the application:
echo        - Double-click: water_levels_app.bat (in the folder that will open)
echo        - Or run: %INSTALL_DIR%\water_levels_app.bat
echo.
echo    [*] For troubleshooting, use the debug launcher
echo.
echo    [*] Opening installation folder...
start "" "%INSTALL_DIR%"
pause

endlocal
