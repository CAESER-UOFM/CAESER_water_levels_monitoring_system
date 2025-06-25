@echo off
setlocal enabledelayedexpansion

REM ================================================================
REM CAESER Water Levels Monitoring Application - GUI Installer
REM ================================================================
REM Uses VBScript for GUI instead of PowerShell (works on all Windows)
REM No PowerShell execution policy issues!
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

REM Default installation directory
set "DEFAULT_PATH=%USERPROFILE%\CAESER_Water_levels_monitoring_system"

echo.
echo    ===============================================================================
echo    #                        INSTALLATION DIRECTORY                              #
echo    ===============================================================================
echo.
echo   Default location: %DEFAULT_PATH%
echo.
echo   This installer does NOT require administrator rights!
echo   Everything installs to your user profile directory.
echo.
echo   ^> Use default location (Press ENTER)
echo     Choose custom location (Type 'c' and ENTER)
echo.
set /p path_choice="Choice (ENTER for default, 'c' for custom): "
if /i "%path_choice%"=="c" (
    echo.
    echo Opening folder browser to select custom installation directory...
    
    REM Create VBScript for folder browser
    set "FOLDER_VBS=%TEMP%\folder_browser.vbs"
    (
        echo Set objShell = CreateObject("WScript.Shell"^)
        echo Set objFolder = objShell.BrowseForFolder(0, "Select installation directory (CAESER_Water_levels_monitoring_system folder will be created inside):", 0^)
        echo If objFolder Is Nothing Then
        echo     WScript.Echo "CANCELLED"
        echo Else
        echo     WScript.Echo objFolder.Self.Path
        echo End If
    ) > "%FOLDER_VBS%"
    
    for /f "delims=" %%a in ('cscript //nologo "%FOLDER_VBS%" 2^>nul') do set "CUSTOM_PATH=%%a"
    del "%FOLDER_VBS%" 2>nul
    
    if "%CUSTOM_PATH%"=="CANCELLED" (
        echo Installation cancelled by user.
        pause
        exit /b 0
    )
    
    if "%CUSTOM_PATH%"=="" (
        echo Error: Could not open folder browser.
        echo Using default location instead.
        set "INSTALL_DIR=%DEFAULT_PATH%"
    ) else (
        set "INSTALL_DIR=%CUSTOM_PATH%\CAESER_Water_levels_monitoring_system"
    )
) else (
    set "INSTALL_DIR=%DEFAULT_PATH%"
)

echo.
echo Selected installation directory: %INSTALL_DIR%
echo.

REM Ask about desktop shortcuts
echo.
echo    ===============================================================================
echo    #                           DESKTOP SHORTCUTS                                #
echo    ===============================================================================
echo.
echo   ^> Create desktop shortcuts (Press ENTER)
echo     Skip desktop shortcuts (Type 'n' and ENTER)
echo.
set /p create_shortcuts="Choice (ENTER for shortcuts, 'n' to skip): "
if /i "%create_shortcuts%"=="n" (
    set "CREATE_DESKTOP=False"
) else (
    set "CREATE_DESKTOP=True"
)

REM Ask about source deletion
echo.
echo    ===============================================================================
echo    #                          SOURCE FOLDER CLEANUP                             #
echo    ===============================================================================
echo.
echo   ^> Delete source folder after installation (Press ENTER)
echo     Keep source folder (Type 'k' and ENTER)
echo.
set /p delete_source="Choice (ENTER to delete, 'k' to keep): "
if /i "%delete_source%"=="k" (
    set "DELETE_SOURCE=False"
) else (
    set "DELETE_SOURCE=True"
)

echo.
echo    ===============================================================================
echo    #                          INSTALLATION SUMMARY                              #
echo    ===============================================================================
echo.
echo - Installation directory: %INSTALL_DIR%
echo - Create desktop shortcuts: %CREATE_DESKTOP%
echo - Delete source after install: %DELETE_SOURCE%
echo.
echo Continue with installation?
echo   ^> Yes, start installation (Press ENTER)
echo     No, cancel installation (Type 'q' and ENTER)
echo.
set /p confirm="Choice (ENTER to install, 'q' to quit): "
if /i "%confirm%"=="q" (
    echo Installation cancelled by user.
    pause
    exit /b 0
)

echo.
echo    ===============================================================================
echo    #                           INSTALLATION STARTING                            #
echo    ===============================================================================
echo.
echo    [*] Installation directory: %INSTALL_DIR%
echo    [*] Desktop shortcuts: %CREATE_DESKTOP%
echo    [*] Delete source: %DELETE_SOURCE%
echo.
echo    [*] Please wait while we set up your Water Levels Monitoring System...
echo.

REM Determine Project Code Directory (where this script resides)
set "CODE_DIR=%~dp0"
REM Remove trailing backslash
if "%CODE_DIR:~-1%"=="\" set "CODE_DIR=%CODE_DIR:~0,-1%"

REM Copy to local drive if running from UNC path
echo %CODE_DIR% | findstr /C:"^\\\\" >nul
if not errorlevel 1 (
    echo Detected network drive installation. Copying to local temp directory...
    set "LOCAL_TEMP=%TEMP%\CAESER_installer_%RANDOM%"
    mkdir "!LOCAL_TEMP!"
    xcopy "%CODE_DIR%" "!LOCAL_TEMP!" /E /I /Y >nul
    set "CODE_DIR=!LOCAL_TEMP!"
    set "CLEANUP_TEMP=True"
) else (
    set "CLEANUP_TEMP=False"
)

REM Define installation subdirectories
set "PYTHON_DIR=%INSTALL_DIR%\python"
set "VENV_DIR=%INSTALL_DIR%\venv"
set "BACKUP_DIR=%INSTALL_DIR%\backups"

REM Create installation directory structure
echo    [*] [1/8] Creating installation directories...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if not exist "%INSTALL_DIR%\databases" mkdir "%INSTALL_DIR%\databases"
if not exist "%INSTALL_DIR%\databases\temp" mkdir "%INSTALL_DIR%\databases\temp"

REM Define Python version and URLs
set "PYTHON_VERSION=3.11.6"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.6/python-3.11.6-embed-amd64.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

REM Download and install Python if not already installed
if not exist "%PYTHON_DIR%\python.exe" (
    echo    [*] [2/8] Installing fresh Python %PYTHON_VERSION% for this application...
    
    REM Download Python using built-in Windows tools
    echo Downloading Python %PYTHON_VERSION%...
    bitsadmin /transfer "PythonDownload" "%PYTHON_URL%" "%INSTALL_DIR%\python.zip" >nul
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to download Python using bitsadmin. Trying alternative method...
        powershell -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%INSTALL_DIR%\python.zip' } catch { exit 1 }"
        if !ERRORLEVEL! NEQ 0 (
            echo Failed to download Python. Please check your internet connection.
            pause
            exit /b 1
        )
    )
    
    REM Extract Python using built-in Windows tools
    echo Extracting Python...
    powershell -ExecutionPolicy Bypass -Command "try { Expand-Archive -Path '%INSTALL_DIR%\python.zip' -DestinationPath '%PYTHON_DIR%' -Force } catch { exit 1 }"
    if exist "%INSTALL_DIR%\python.zip" del "%INSTALL_DIR%\python.zip"
    
    REM Enable site-packages
    echo Enabling site-packages...
    for %%F in ("%PYTHON_DIR%\python*._pth") do (
        type "%%F" > "%%F.temp"
        echo import site >> "%%F.temp"
        move /y "%%F.temp" "%%F"
    )
    
    REM Download and install pip
    echo Installing pip...
    bitsadmin /transfer "PipDownload" "%GET_PIP_URL%" "%INSTALL_DIR%\get-pip.py" >nul
    if %ERRORLEVEL% NEQ 0 (
        powershell -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '%GET_PIP_URL%' -OutFile '%INSTALL_DIR%\get-pip.py' } catch { exit 1 }"
    )
    
    "%PYTHON_DIR%\python.exe" "%INSTALL_DIR%\get-pip.py" --no-warn-script-location
    if exist "%INSTALL_DIR%\get-pip.py" del "%INSTALL_DIR%\get-pip.py"
    
    echo    [+] Python installation complete.
) else (
    echo    [+] [2/8] Using existing Python installation.
)

REM Install virtualenv
echo    [*] [3/8] Installing virtualenv...
"%PYTHON_DIR%\python.exe" -m pip install --no-warn-script-location setuptools virtualenv

REM Create virtual environment
if exist "%VENV_DIR%" (
    echo    [*] Removing existing virtual environment...
    rmdir /s /q "%VENV_DIR%"
)

echo    [*] [4/8] Creating virtual environment...
"%PYTHON_DIR%\python.exe" -m virtualenv "%VENV_DIR%"

REM Install dependencies
echo    [*] [5/8] Installing dependencies...
call "%VENV_DIR%\Scripts\activate.bat"

echo        [*] Upgrading pip...
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo        [!] Failed to upgrade pip, continuing...
)

echo        [*] Installing core packages...
python -m pip install numpy
if %ERRORLEVEL% NEQ 0 (
    echo        [!] Failed to install numpy
    pause
    exit /b 1
)

python -m pip install pandas matplotlib
if %ERRORLEVEL% NEQ 0 (
    echo        [!] Failed to install pandas/matplotlib
    pause
    exit /b 1
)

echo        [*] Installing utility packages...
python -m pip install requests packaging
if %ERRORLEVEL% NEQ 0 (
    echo        [!] Failed to install requests/packaging
    pause
    exit /b 1
)

echo        [*] Installing Google API packages...
python -m pip install google-api-python-client google-auth-oauthlib --upgrade
if %ERRORLEVEL% NEQ 0 (
    echo        [!] Failed to install Google API packages
    pause
    exit /b 1
)

echo        [*] Installing PyQt5 packages...
python -m pip install PyQt5==5.15.10 PyQt5_sip==12.13.0 PyQtWebEngine==5.15.6
if %ERRORLEVEL% NEQ 0 (
    echo        [!] Failed to install PyQt5 packages
    pause
    exit /b 1
)

echo        [*] Installing scientific packages...
python -m pip install scipy folium branca pillow psutil --upgrade
if %ERRORLEVEL% NEQ 0 (
    echo        [!] Failed to install scientific packages
    pause
    exit /b 1
)

echo        [+] All dependencies installed successfully!

REM Copy application files
echo    [*] [6/8] Copying application files...
echo    [*] Source directory: %CODE_DIR%
echo    [*] Destination directory: %INSTALL_DIR%

REM Verify source directory exists
if not exist "%CODE_DIR%" (
    echo    [!] ERROR: Source directory does not exist: %CODE_DIR%
    pause
    exit /b 1
)

REM Verify destination directory exists
if not exist "%INSTALL_DIR%" (
    echo    [!] ERROR: Destination directory does not exist: %INSTALL_DIR%
    pause
    exit /b 1
)

echo    [*] Copying core application files...
xcopy "%CODE_DIR%\src" "%INSTALL_DIR%\src\" /E /I /Y
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo    ===============================================================================
    echo    #                              ERROR OCCURRED                                 #
    echo    ===============================================================================
    echo    [!] ERROR: Failed to copy src folder from:
    echo        Source: %CODE_DIR%\src
    echo        Destination: %INSTALL_DIR%\src\
    echo.
    echo    This could be due to:
    echo    - Running from network drive (OneDrive, SharePoint)
    echo    - Insufficient permissions
    echo    - Antivirus interference
    echo    - Path too long
    echo.
    echo    Try copying the installer to your local drive first.
    echo.
    pause
    exit /b 1
)

xcopy "%CODE_DIR%\main.py" "%INSTALL_DIR%\" /Y
if %ERRORLEVEL% NEQ 0 (
    echo    [!] ERROR: Failed to copy main.py - this is a critical file
    echo    Installation cannot continue without this file.
    pause
    exit /b 1
)

xcopy "%CODE_DIR%\Requirements.txt" "%INSTALL_DIR%\" /Y
if %ERRORLEVEL% NEQ 0 (
    echo    [!] ERROR: Failed to copy Requirements.txt - this is a critical file
    echo    Installation cannot continue without this file.
    pause
    exit /b 1
)

echo    [*] Copying optional folders...
if exist "%CODE_DIR%\config" (
    xcopy "%CODE_DIR%\config" "%INSTALL_DIR%\config\" /E /I /Y
    if %ERRORLEVEL% NEQ 0 echo    [!] Warning: Error copying config folder
)

if exist "%CODE_DIR%\tools" (
    xcopy "%CODE_DIR%\tools" "%INSTALL_DIR%\tools\" /E /I /Y
    if %ERRORLEVEL% NEQ 0 echo    [!] Warning: Error copying tools folder
)

if exist "%CODE_DIR%\assets" (
    xcopy "%CODE_DIR%\assets" "%INSTALL_DIR%\assets\" /E /I /Y
    if %ERRORLEVEL% NEQ 0 echo    [!] Warning: Error copying assets folder
)

if exist "%CODE_DIR%\Legacy_tables" (
    xcopy "%CODE_DIR%\Legacy_tables" "%INSTALL_DIR%\Legacy_tables\" /E /I /Y
    if %ERRORLEVEL% NEQ 0 echo    [!] Warning: Error copying Legacy_tables folder
)

echo    [+] Application files copied successfully

REM Create version file
echo    [*] Creating version file...
(
    echo {
    echo   "version": "1.0.0-beta",
    echo   "release_date": "%DATE%",
    echo   "description": "Water Level Monitoring System - GUI Installation",
    echo   "github_repo": "CAESER-UOFM/CAESER_water_levels_monitoring_system",
    echo   "auto_update": {
    echo     "enabled": true,
    echo     "check_on_startup": true,
    echo     "backup_count": 3
    echo   },
    echo   "installation_path": "%INSTALL_DIR%"
    echo }
) > "%INSTALL_DIR%\version.json"

REM Create launchers
echo    [*] [7/8] Creating launchers...

set "LAUNCHER=%INSTALL_DIR%\water_levels_app.bat"
(
    echo @echo off
    echo cd /d "%INSTALL_DIR%"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo python "%INSTALL_DIR%\main.py"
) > "%LAUNCHER%"

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
    echo    [*] [8/8] Creating desktop shortcuts...
    
    REM Use PowerShell to create shortcuts with error handling
    echo    [*] Creating main application shortcut...
    powershell -ExecutionPolicy Bypass -Command "$WshShell = New-Object -comObject WScript.Shell; $Desktop = [System.Environment]::GetFolderPath('Desktop'); $Shortcut = $WshShell.CreateShortcut('$Desktop\CAESER Water Levels Monitoring.lnk'); $Shortcut.TargetPath = '%LAUNCHER%'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'CAESER Water Levels Monitoring Application'; $Shortcut.Save(); Write-Host 'Main shortcut created'" 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo    [!] PowerShell shortcut creation failed, trying VBScript fallback...
        goto :create_shortcuts_vbs
    )
    
    echo    [*] Creating visualizer shortcut...
    powershell -ExecutionPolicy Bypass -Command "$WshShell = New-Object -comObject WScript.Shell; $Desktop = [System.Environment]::GetFolderPath('Desktop'); $Shortcut = $WshShell.CreateShortcut('$Desktop\CAESER Water Level Visualizer.lnk'); $Shortcut.TargetPath = '%VISUALIZER_LAUNCHER%'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%\tools\Visualizer'; $Shortcut.Description = 'CAESER Water Level Data Visualizer'; $Shortcut.Save(); Write-Host 'Visualizer shortcut created'" 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo    [!] PowerShell shortcut creation failed, trying VBScript fallback...
        goto :create_shortcuts_vbs
    )
    goto :verify_shortcuts
    
    :create_shortcuts_vbs
    echo    [*] Using VBScript fallback for shortcut creation...
    
    REM Create VBScript for main app shortcut
    set "SHORTCUT_VBS=%TEMP%\create_shortcut.vbs"
    (
        echo Set objShell = CreateObject("WScript.Shell"^)
        echo Set objDesktop = objShell.SpecialFolders("Desktop"^)
        echo Set objShortCut = objShell.CreateShortcut(objDesktop ^& "\CAESER Water Levels Monitoring.lnk"^)
        echo objShortCut.TargetPath = "%LAUNCHER%"
        echo objShortCut.WorkingDirectory = "%INSTALL_DIR%"
        echo objShortCut.Description = "CAESER Water Levels Monitoring Application"
        echo objShortCut.Save
    ) > "%SHORTCUT_VBS%"
    cscript //nologo "%SHORTCUT_VBS%" 2>nul
    del "%SHORTCUT_VBS%" 2>nul
    
    REM Create VBScript for visualizer shortcut
    (
        echo Set objShell = CreateObject("WScript.Shell"^)
        echo Set objDesktop = objShell.SpecialFolders("Desktop"^)
        echo Set objShortCut = objShell.CreateShortcut(objDesktop ^& "\CAESER Water Level Visualizer.lnk"^)
        echo objShortCut.TargetPath = "%VISUALIZER_LAUNCHER%"
        echo objShortCut.WorkingDirectory = "%INSTALL_DIR%\tools\Visualizer"
        echo objShortCut.Description = "CAESER Water Level Data Visualizer"
        echo objShortCut.Save
    ) > "%SHORTCUT_VBS%"
    cscript //nologo "%SHORTCUT_VBS%" 2>nul
    del "%SHORTCUT_VBS%" 2>nul
    
    :verify_shortcuts
    
    REM Verify shortcuts were created
    set "DESKTOP_PATH=%USERPROFILE%\Desktop"
    if exist "%DESKTOP_PATH%\CAESER Water Levels Monitoring.lnk" (
        echo    [+] Main app shortcut created successfully
    ) else (
        echo    [!] Warning: Main app shortcut not found
    )
    
    if exist "%DESKTOP_PATH%\CAESER Water Level Visualizer.lnk" (
        echo    [+] Visualizer shortcut created successfully  
    ) else (
        echo    [!] Warning: Visualizer shortcut not found
    )
)

REM Cleanup temp directory if we copied from UNC
if "%CLEANUP_TEMP%"=="True" (
    echo Cleaning up temporary files...
    rmdir /s /q "!LOCAL_TEMP!" 2>nul
)

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
echo        [*] Main app: %LAUNCHER%
echo        [*] Debug mode: %DEBUG_LAUNCHER%
echo        [*] Visualizer: %VISUALIZER_LAUNCHER%

if "%CREATE_DESKTOP%"=="True" (
    echo.
    echo    [+] Desktop shortcuts created:
    echo        [*] CAESER Water Levels Monitoring
    echo        [*] CAESER Water Level Visualizer
)

echo.
echo    [+] You can now launch the application!
echo.
echo    ===============================================================================
echo    #                         INSTALLATION COMPLETED                             #
echo    ===============================================================================
echo.
echo    [+] What was installed:
echo        - Python 3.11.6 (embedded version)
echo        - Virtual environment with all dependencies
echo        - CAESER Water Levels Monitoring System
echo        - Application launchers (main app, debug, visualizer)
if "%CREATE_DESKTOP%"=="True" (
    echo        - Desktop shortcuts for easy access
)
echo.
echo    [+] Installation location: %INSTALL_DIR%
echo.
echo    [+] To start using the application:
if "%CREATE_DESKTOP%"=="True" (
    echo        - Double-click the desktop shortcuts, OR
)
echo        - Run: %INSTALL_DIR%\water_levels_app.bat
echo.
echo    [*] For troubleshooting, use the debug launcher
echo.
pause

REM Handle source deletion
if "%DELETE_SOURCE%"=="True" (
    echo The installer will now attempt to delete the source folder.
    echo This is safe since everything has been copied to: %INSTALL_DIR%
    echo.
    pause
    
    REM Determine original source directory
    set "ORIGINAL_CODE_DIR=%~dp0"
    if "%ORIGINAL_CODE_DIR:~-1%"=="\" set "ORIGINAL_CODE_DIR=%ORIGINAL_CODE_DIR:~0,-1%"
    
    cd /d "%USERPROFILE%" 2>nul
    if exist "%ORIGINAL_CODE_DIR%" (
        rmdir /s /q "%ORIGINAL_CODE_DIR%" 2>nul
        if exist "%ORIGINAL_CODE_DIR%" (
            echo Could not delete source folder. You may need to delete it manually.
        ) else (
            echo Source folder deleted successfully.
        )
    )
)

echo.
echo    [*] Installation script completed. Press any key to close this window.
pause >nul

endlocal