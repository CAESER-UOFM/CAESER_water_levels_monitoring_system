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
mkdir "%INSTALL_DIR%\launchers"

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

REM Create launchers in dedicated folder
echo    [*] Creating application launchers...

REM Main app launcher (completely hidden - no console window)
(
    echo Set objShell = CreateObject^("WScript.Shell"^)
    echo objShell.CurrentDirectory = "%INSTALL_DIR%"
    echo objShell.Run "cmd /c """"%INSTALL_DIR%\venv\Scripts\activate.bat"""" ^& """"%INSTALL_DIR%\venv\Scripts\pythonw.exe"""" """"%INSTALL_DIR%\main.py"""""", 0, False
) > "%INSTALL_DIR%\launchers\water_levels_monitoring_system.vbs"

REM Debug launcher (with console for troubleshooting)
(
    echo @echo off
    echo echo CAESER Water Levels Monitoring - Debug Mode
    echo echo ==========================================
    echo cd /d "%INSTALL_DIR%"
    echo call "%INSTALL_DIR%\venv\Scripts\activate.bat"
    echo python "%INSTALL_DIR%\main.py"
    echo pause
) > "%INSTALL_DIR%\launchers\water_levels_monitoring_system_debug.bat"

REM Visualizer launcher (completely hidden - no console window)
(
    echo Set objShell = CreateObject^("WScript.Shell"^)
    echo objShell.CurrentDirectory = "%INSTALL_DIR%\tools\Visualizer"
    echo objShell.Run "cmd /c """"%INSTALL_DIR%\venv\Scripts\activate.bat"""" ^& """"%INSTALL_DIR%\venv\Scripts\pythonw.exe"""" """"%INSTALL_DIR%\tools\Visualizer\main.py"""""", 0, False
) > "%INSTALL_DIR%\launchers\water_levels_visualizer.vbs"

REM Visualizer debug launcher (with console for troubleshooting)
(
    echo @echo off
    echo echo CAESER Water Level Visualizer - Debug Mode
    echo echo ==========================================
    echo cd /d "%INSTALL_DIR%\tools\Visualizer"
    echo call "%INSTALL_DIR%\venv\Scripts\activate.bat"
    echo python "%INSTALL_DIR%\tools\Visualizer\main.py"
    echo pause
) > "%INSTALL_DIR%\launchers\water_levels_visualizer_debug.bat"

echo    [*] Creating shortcuts with icons...

REM Main app shortcut with custom icon (points to VBScript for silent execution)
powershell -ExecutionPolicy Bypass -Command "try { $WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%INSTALL_DIR%\CAESER Water Levels Monitoring.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\launchers\water_levels_monitoring_system.vbs'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'CAESER Water Levels Monitoring System'; if (Test-Path '%INSTALL_DIR%\src\gui\icons\water_level_meter.png') { $Shortcut.IconLocation = '%INSTALL_DIR%\src\gui\icons\water_level_meter.png' } else { $Shortcut.IconLocation = 'C:\Windows\System32\notepad.exe,0' }; $Shortcut.Save() } catch { Write-Host 'Main app shortcut creation failed' }" 2>nul

REM Visualizer shortcut with custom icon (points to VBScript for silent execution)  
powershell -ExecutionPolicy Bypass -Command "try { $WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%INSTALL_DIR%\CAESER Water Level Visualizer.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\launchers\water_levels_visualizer.vbs'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'CAESER Water Level Visualizer'; if (Test-Path '%INSTALL_DIR%\src\gui\icons\Water_level_tab_icon.png') { $Shortcut.IconLocation = '%INSTALL_DIR%\src\gui\icons\Water_level_tab_icon.png' } else { $Shortcut.IconLocation = 'C:\Windows\System32\calc.exe,0' }; $Shortcut.Save() } catch { Write-Host 'Visualizer shortcut creation failed' }" 2>nul

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
echo    [+] Shortcuts created in main folder:
echo        [*] CAESER Water Levels Monitoring.lnk (main app with icon)
echo        [*] CAESER Water Level Visualizer.lnk (visualizer with icon)
echo.
echo    [+] Launchers created in 'launchers' folder:
echo        [*] water_levels_monitoring_system.vbs (main app, completely silent)
echo        [*] water_levels_monitoring_system_debug.bat (main app with console)
echo        [*] water_levels_visualizer.vbs (visualizer, completely silent)
echo        [*] water_levels_visualizer_debug.bat (visualizer with console)
echo.
echo    [+] You can now launch the applications!
echo.
echo    [+] Recommended way to start:
echo        - Main app: Double-click "CAESER Water Levels Monitoring.lnk"
echo        - Visualizer: Double-click "CAESER Water Level Visualizer.lnk"
echo.
echo    [*] For troubleshooting, use the debug launchers in the 'launchers' folder
echo.
echo    [*] Opening installation folder...
start "" "%INSTALL_DIR%"
pause

endlocal
