@echo off
setlocal enabledelayedexpansion

REM ================================================================
REM CAESER Water Levels Monitoring Application - User Installer
REM ================================================================
REM This installer does NOT require administrator rights!
REM Everything installs to your user profile directory.
REM Safe for university/corporate computers with limited permissions.
REM ================================================================

REM Determine Project Code Directory (where this script resides)
set "CODE_DIR=%~dp0"
REM Remove trailing backslash
if "%CODE_DIR:~-1%"=="\" set "CODE_DIR=%CODE_DIR:~0,-1%"

REM Show installation dialog and get user choices
echo Loading installation dialog...
for /f "tokens=1,2 delims=|" %%a in ('powershell -ExecutionPolicy Bypass -Command "
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Create main form
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Water Levels Monitoring - User Installation (No Admin Required)'
$form.Size = New-Object System.Drawing.Size(520, 445)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(240, 248, 255)

# Create header panel
$headerPanel = New-Object System.Windows.Forms.Panel
$headerPanel.Size = New-Object System.Drawing.Size(520, 80)
$headerPanel.BackColor = [System.Drawing.Color]::FromArgb(70, 130, 180)
$headerPanel.Dock = 'Top'
$form.Controls.Add($headerPanel)

# Title label
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = 'Water Levels Monitoring System'
$titleLabel.Font = New-Object System.Drawing.Font('Segoe UI', 16, [System.Drawing.FontStyle]::Bold)
$titleLabel.ForeColor = [System.Drawing.Color]::White
$titleLabel.AutoSize = $true
$titleLabel.Location = New-Object System.Drawing.Point(20, 15)
$headerPanel.Controls.Add($titleLabel)

$subtitleLabel = New-Object System.Windows.Forms.Label
$subtitleLabel.Text = 'Professional Installation Setup'
$subtitleLabel.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$subtitleLabel.ForeColor = [System.Drawing.Color]::LightGray
$subtitleLabel.AutoSize = $true
$subtitleLabel.Location = New-Object System.Drawing.Point(20, 45)
$headerPanel.Controls.Add($subtitleLabel)

# Installation path section
$pathLabel = New-Object System.Windows.Forms.Label
$pathLabel.Text = 'Installation Directory:'
$pathLabel.Font = New-Object System.Drawing.Font('Segoe UI', 10, [System.Drawing.FontStyle]::Bold)
$pathLabel.Location = New-Object System.Drawing.Point(20, 100)
$pathLabel.Size = New-Object System.Drawing.Size(200, 25)
$form.Controls.Add($pathLabel)

$pathTextBox = New-Object System.Windows.Forms.TextBox
$pathTextBox.Text = '$env:USERPROFILE\WaterLevelsApp'
$pathTextBox.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$pathTextBox.Location = New-Object System.Drawing.Point(20, 125)
$pathTextBox.Size = New-Object System.Drawing.Size(350, 25)
$form.Controls.Add($pathTextBox)

$browseButton = New-Object System.Windows.Forms.Button
$browseButton.Text = 'Browse...'
$browseButton.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$browseButton.Location = New-Object System.Drawing.Point(380, 124)
$browseButton.Size = New-Object System.Drawing.Size(80, 27)
$browseButton.BackColor = [System.Drawing.Color]::FromArgb(70, 130, 180)
$browseButton.ForeColor = [System.Drawing.Color]::White
$browseButton.FlatStyle = 'Flat'
$browseButton.Add_Click({
    $folderDialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $folderDialog.Description = 'Select Installation Directory'
    $folderDialog.SelectedPath = $pathTextBox.Text
    if ($folderDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $pathTextBox.Text = $folderDialog.SelectedPath + '\WaterLevelsApp'
    }
})
$form.Controls.Add($browseButton)

# Warning section
$warningPanel = New-Object System.Windows.Forms.Panel
$warningPanel.Location = New-Object System.Drawing.Point(20, 165)
$warningPanel.Size = New-Object System.Drawing.Size(460, 120)
$warningPanel.BackColor = [System.Drawing.Color]::FromArgb(255, 248, 220)
$warningPanel.BorderStyle = 'FixedSingle'
$form.Controls.Add($warningPanel)

$warningIcon = New-Object System.Windows.Forms.Label
$warningIcon.Text = '⚠️'
$warningIcon.Font = New-Object System.Drawing.Font('Segoe UI', 16)
$warningIcon.Location = New-Object System.Drawing.Point(10, 10)
$warningIcon.Size = New-Object System.Drawing.Size(30, 30)
$warningPanel.Controls.Add($warningIcon)

$warningTitle = New-Object System.Windows.Forms.Label
$warningTitle.Text = 'Important Notice'
$warningTitle.Font = New-Object System.Drawing.Font('Segoe UI', 10, [System.Drawing.FontStyle]::Bold)
$warningTitle.Location = New-Object System.Drawing.Point(50, 10)
$warningTitle.Size = New-Object System.Drawing.Size(200, 25)
$warningPanel.Controls.Add($warningTitle)

$warningText = New-Object System.Windows.Forms.Label
$warningText.Text = 'This installer works without administrator rights - everything installs to your user folder. The application will be copied to your personal directory. After successful installation, you can optionally delete this source folder.'
$warningText.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$warningText.Location = New-Object System.Drawing.Point(10, 40)
$warningText.Size = New-Object System.Drawing.Size(440, 60)
$warningPanel.Controls.Add($warningText)

# Desktop shortcuts checkbox
$desktopCheckbox = New-Object System.Windows.Forms.CheckBox
$desktopCheckbox.Text = 'Create desktop shortcuts for easy access (Recommended)'
$desktopCheckbox.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$desktopCheckbox.Location = New-Object System.Drawing.Point(20, 300)
$desktopCheckbox.Size = New-Object System.Drawing.Size(400, 25)
$desktopCheckbox.Checked = $true
$form.Controls.Add($desktopCheckbox)

# Delete source checkbox
$deleteCheckbox = New-Object System.Windows.Forms.CheckBox
$deleteCheckbox.Text = 'Delete source folder after successful installation (Recommended)'
$deleteCheckbox.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$deleteCheckbox.Location = New-Object System.Drawing.Point(20, 325)
$deleteCheckbox.Size = New-Object System.Drawing.Size(400, 25)
$deleteCheckbox.Checked = $true
$form.Controls.Add($deleteCheckbox)

# Buttons
$installButton = New-Object System.Windows.Forms.Button
$installButton.Text = 'Install Application'
$installButton.Font = New-Object System.Drawing.Font('Segoe UI', 10, [System.Drawing.FontStyle]::Bold)
$installButton.Location = New-Object System.Drawing.Point(280, 365)
$installButton.Size = New-Object System.Drawing.Size(120, 35)
$installButton.BackColor = [System.Drawing.Color]::FromArgb(34, 139, 34)
$installButton.ForeColor = [System.Drawing.Color]::White
$installButton.FlatStyle = 'Flat'
$installButton.Add_Click({
    $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $form.Close()
})
$form.Controls.Add($installButton)

$cancelButton = New-Object System.Windows.Forms.Button
$cancelButton.Text = 'Cancel'
$cancelButton.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$cancelButton.Location = New-Object System.Drawing.Point(410, 365)
$cancelButton.Size = New-Object System.Drawing.Size(80, 35)
$cancelButton.BackColor = [System.Drawing.Color]::FromArgb(220, 20, 60)
$cancelButton.ForeColor = [System.Drawing.Color]::White
$cancelButton.FlatStyle = 'Flat'
$cancelButton.Add_Click({
    $form.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $form.Close()
})
$form.Controls.Add($cancelButton)

# Show dialog and return results
$result = $form.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output ($pathTextBox.Text + '|' + $deleteCheckbox.Checked + '|' + $desktopCheckbox.Checked)
} else {
    Write-Output 'CANCELLED|false|false'
}
"') do (
    set "INSTALL_DIR=%%a"
    set "DELETE_SOURCE=%%b"
    set "CREATE_DESKTOP=%%c"
)

REM Check if user cancelled
if "%INSTALL_DIR%"=="CANCELLED" (
    echo Installation cancelled by user.
    pause
    exit /b 0
)

REM Expand environment variables in path
call set "INSTALL_DIR=%INSTALL_DIR%"

echo ===============================================
echo Water Levels Monitoring Application Setup
echo Enhanced Installation with Auto-Update System
echo ===============================================
echo Installation directory: %INSTALL_DIR%
echo Delete source after install: %DELETE_SOURCE%
echo Create desktop shortcuts: %CREATE_DESKTOP%
echo.

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
    echo   "version": "1.0.0",
    echo   "release_date": "%DATE%",
    echo   "description": "Water Level Monitoring System - Initial Installation",
    echo   "github_repo": "benjaled/water_levels_monitoring_-for_external_edits-",
    echo   "auto_update": {
    echo     "enabled": true,
    echo     "check_on_startup": true,
    echo     "backup_count": 3
    echo   },
    echo   "installation_path": "%INSTALL_DIR%"
    echo }
) > "%INSTALL_DIR%\version.json"

REM Create enhanced launcher script with auto-update check
set "LAUNCHER=%INSTALL_DIR%\water_levels_app.bat"
(
    echo @echo off
    echo REM Water Levels Monitoring Application Launcher
    echo REM With Auto-Update Support
    echo.
    echo cd /d "%INSTALL_DIR%"
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
    echo "%VENV_DIR%\Scripts\python.exe" "%INSTALL_DIR%\main.py"
) > "%LAUNCHER%"

REM Create debug launcher script
set "DEBUG_LAUNCHER=%INSTALL_DIR%\water_levels_app_debug.bat"
(
    echo @echo off
    echo echo Water Levels Monitoring Application - Debug Mode
    echo echo =============================================
    echo cd /d "%INSTALL_DIR%"
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
    echo python "%INSTALL_DIR%\main.py"
    echo.
    echo echo Application ended. Press any key to close...
    echo pause ^>nul
) > "%DEBUG_LAUNCHER%"

REM Create visualizer launcher script
set "VISUALIZER_LAUNCHER=%INSTALL_DIR%\water_level_visualizer_app.bat"
(
    echo @echo off
    echo cd /d "%INSTALL_DIR%\tools\Visualizer"
    echo call "%VENV_DIR%\Scripts\activate.bat"
    echo if not exist "%VENV_DIR%\Lib\site-packages\matplotlib" ^(
    echo     echo Installing missing matplotlib package. Please wait...
    echo     python -m pip install pandas matplotlib scipy --upgrade
    echo ^)
    echo python "%INSTALL_DIR%\tools\Visualizer\main.py"
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

REM Create desktop shortcuts if requested
if "%CREATE_DESKTOP%"=="True" (
    echo Creating desktop shortcuts...
    
    REM Get desktop path
    for /f "usebackq tokens=3*" %%A in (`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v Desktop 2^>nul`) do set "DESKTOP_PATH=%%A %%B"
    if not defined DESKTOP_PATH set "DESKTOP_PATH=%USERPROFILE%\Desktop"
    
    REM Create main application shortcut
    powershell -Command "
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut('%DESKTOP_PATH%\Water Levels Monitoring.lnk')
        $Shortcut.TargetPath = '%LAUNCHER%'
        $Shortcut.WorkingDirectory = '%INSTALL_DIR%'
        $Shortcut.Description = 'CAESER Water Levels Monitoring Application'
        $Shortcut.Save()
    "
    
    REM Create debug shortcut
    powershell -Command "
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut('%DESKTOP_PATH%\Water Levels Monitoring (Debug).lnk')
        $Shortcut.TargetPath = '%DEBUG_LAUNCHER%'
        $Shortcut.WorkingDirectory = '%INSTALL_DIR%'
        $Shortcut.Description = 'CAESER Water Levels Monitoring - Debug Mode'
        $Shortcut.Save()
    "
    
    REM Create visualizer shortcut
    powershell -Command "
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut('%DESKTOP_PATH%\Water Level Visualizer.lnk')
        $Shortcut.TargetPath = '%VISUALIZER_LAUNCHER%'
        $Shortcut.WorkingDirectory = '%INSTALL_DIR%\tools\Visualizer'
        $Shortcut.Description = 'CAESER Water Level Data Visualizer'
        $Shortcut.Save()
    "
    
    echo Desktop shortcuts created successfully.
    echo.
)

echo.
echo ===============================================
echo Setup Complete!
echo ===============================================
echo.
echo Installation directory: %INSTALL_DIR%
echo Application files: %INSTALL_DIR%
echo.
echo Launchers created:
echo   Main app: %LAUNCHER%
echo   Debug mode: %DEBUG_LAUNCHER%
echo   Visualizer: %VISUALIZER_LAUNCHER%
echo   Uninstaller: %UNINSTALLER%
if "%CREATE_DESKTOP%"=="True" (
    echo.
    echo Desktop shortcuts created:
    echo   📱 Water Levels Monitoring
    echo   🐛 Water Levels Monitoring ^(Debug^)
    echo   📊 Water Level Visualizer
)
echo.
echo Features included:
echo   ✓ Isolated Python environment
echo   ✓ All dependencies installed
echo   ✓ Auto-update system enabled
echo   ✓ Backup system for safe updates
echo   ✓ Debug mode for troubleshooting
echo   ✓ Easy uninstall option
if "%CREATE_DESKTOP%"=="True" (
    echo   ✓ Desktop shortcuts for easy access
)
echo.
if "%CREATE_DESKTOP%"=="True" (
    echo Desktop shortcuts are ready for immediate use.
) else (
    echo You can manually copy the launchers to your desktop for easy access.
)
echo The application will automatically check for updates on startup.
echo.

REM Handle source folder deletion if requested
if "%DELETE_SOURCE%"=="True" (
    echo ===============================================
    echo Source Folder Cleanup
    echo ===============================================
    echo.
    echo The installation was successful. Would you like to delete the
    echo source folder to avoid having duplicate files?
    echo.
    echo Source folder: %CODE_DIR%
    echo Installation: %INSTALL_DIR%
    echo.
    set /p confirm="Delete source folder? (Y/n): "
    if /i "!confirm!" NEQ "n" (
        echo.
        echo Deleting source folder...
        cd /d "%USERPROFILE%"
        if exist "%CODE_DIR%" (
            rmdir /s /q "%CODE_DIR%"
            echo Source folder deleted successfully.
        ) else (
            echo Source folder not found or already deleted.
        )
    ) else (
        echo Source folder kept. You can manually delete it later if needed.
    )
    echo.
)

echo For troubleshooting, use the debug launcher to see detailed error messages.
echo.
echo Installation complete. Press any key to exit...
pause
endlocal