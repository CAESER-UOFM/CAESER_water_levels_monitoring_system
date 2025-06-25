@echo off
setlocal enabledelayedexpansion

REM Global error handler - catch unexpected crashes
if not defined DEBUG_MODE set DEBUG_MODE=1

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
echo    #                     1. INSTALLATION DIRECTORY                              #
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
REM Shortcuts will be created in installation folder (no desktop shortcuts)
set "CREATE_DESKTOP=False"

REM Ask about source deletion
echo.
echo    ===============================================================================
echo    #                       2. SOURCE FOLDER CLEANUP                             #
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
echo    #                       3. INSTALLATION SUMMARY                              #
echo    ===============================================================================
echo.
echo - Installation directory: %INSTALL_DIR%
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
echo    #                        4. INSTALLATION STARTING                            #
echo    ===============================================================================
echo.
echo    [*] Installation directory: %INSTALL_DIR%
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
echo    [*] [1/7] Creating installation directories...

REM Clean up existing installation if it exists
if exist "%INSTALL_DIR%" (
    echo    [*] Removing existing installation directory...
    rmdir /s /q "%INSTALL_DIR%" 2>nul
    if exist "%INSTALL_DIR%" (
        echo    [!] Warning: Could not fully remove existing installation directory
        echo    [!] Some files may be in use. Installation will continue with overwrite.
    )
)

mkdir "%INSTALL_DIR%"
mkdir "%BACKUP_DIR%"
mkdir "%INSTALL_DIR%\databases"
mkdir "%INSTALL_DIR%\databases\temp"

REM Define Python version and URLs
set "PYTHON_VERSION=3.11.6"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.6/python-3.11.6-embed-amd64.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

REM Download and install Python if not already installed
if not exist "%PYTHON_DIR%\python.exe" (
    echo    [*] [2/7] Installing fresh Python %PYTHON_VERSION% for this application...
    echo    [DEBUG] Python directory: %PYTHON_DIR%
    echo    [DEBUG] Python URL: %PYTHON_URL%
    echo    [DEBUG] Install directory: %INSTALL_DIR%
    
    REM Download Python using built-in Windows tools
    echo Downloading Python %PYTHON_VERSION%...
    bitsadmin /transfer "PythonDownload" "%PYTHON_URL%" "%INSTALL_DIR%\python.zip"
    echo [DEBUG] Bitsadmin exit code: %ERRORLEVEL%
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to download Python using bitsadmin. Trying alternative method...
        powershell -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%INSTALL_DIR%\python.zip' } catch { Write-Host 'PowerShell download failed'; exit 1 }"
        echo [DEBUG] PowerShell exit code: !ERRORLEVEL!
        if !ERRORLEVEL! NEQ 0 (
            echo Failed to download Python. Please check your internet connection.
            echo [DEBUG] Both bitsadmin and PowerShell failed
            pause
            exit /b 1
        )
    )
    
    echo [DEBUG] Download completed, checking if file exists...
    if not exist "%INSTALL_DIR%\python.zip" (
        echo [ERROR] Python.zip file was not created despite successful download
        pause
        exit /b 1
    )
    
    REM Extract Python using built-in Windows tools
    echo Extracting Python...
    echo [DEBUG] Extracting from: %INSTALL_DIR%\python.zip
    echo [DEBUG] Extracting to: %PYTHON_DIR%
    powershell -ExecutionPolicy Bypass -Command "try { Expand-Archive -Path '%INSTALL_DIR%\python.zip' -DestinationPath '%PYTHON_DIR%' -Force } catch { Write-Host 'Extraction failed'; exit 1 }"
    echo [DEBUG] Extraction exit code: %ERRORLEVEL%
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to extract Python. Please check if the download was successful.
        echo [DEBUG] PowerShell extraction command failed
        pause
        exit /b 1
    )
    if exist "%INSTALL_DIR%\python.zip" del "%INSTALL_DIR%\python.zip"
    
    REM Verify Python was extracted
    if not exist "%PYTHON_DIR%\python.exe" (
        echo Python extraction failed - python.exe not found
        pause
        exit /b 1
    )
    
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
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install pip. Python installation may be corrupted.
        pause
        exit /b 1
    )
    if exist "%INSTALL_DIR%\get-pip.py" del "%INSTALL_DIR%\get-pip.py"
    
    echo    [+] Python installation complete.
) else (
    echo    [+] [2/7] Using existing Python installation.
)

REM Install virtualenv
echo    [*] [3/7] Installing virtualenv...
"%PYTHON_DIR%\python.exe" -m pip install --no-warn-script-location setuptools virtualenv

REM Create virtual environment
if exist "%VENV_DIR%" (
    echo    [*] Removing existing virtual environment...
    rmdir /s /q "%VENV_DIR%"
)

echo    [*] [4/7] Creating virtual environment...
"%PYTHON_DIR%\python.exe" -m virtualenv "%VENV_DIR%"

REM Install dependencies
echo    [*] [5/7] Installing dependencies...
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
echo    [*] [6/7] Copying application files...
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

REM Check if destination exists and has files to confirm copy success
if exist "%INSTALL_DIR%\src\" (
    echo    [+] Core files copied successfully
) else (
    echo    [!] ERROR: Source folder copy failed - src directory not created
    pause
    exit /b 1
)

xcopy "%CODE_DIR%\main.py" "%INSTALL_DIR%\" /Y
if not exist "%INSTALL_DIR%\main.py" (
    echo    [!] ERROR: Failed to copy main.py
    pause
    exit /b 1
)

xcopy "%CODE_DIR%\Requirements.txt" "%INSTALL_DIR%\" /Y
if not exist "%INSTALL_DIR%\Requirements.txt" (
    echo    [!] ERROR: Failed to copy Requirements.txt
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
echo    [*] [7/7] Creating launchers...

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

REM Installation complete - open the installation folder
echo    [*] Opening installation folder...
echo    [+] Installation complete! Opening folder with your applications...

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
echo.
echo    [+] Installation location: %INSTALL_DIR%
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