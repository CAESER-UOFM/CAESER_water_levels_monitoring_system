@echo off
setlocal enabledelayedexpansion

REM ================================================================
REM CAESER Water Levels Monitoring Application - DEBUG Installer
REM ================================================================
REM Enhanced logging to debug icon and app launch issues
REM ================================================================

cls
echo.
echo    ===============================================================================
echo    #                       DEBUG INSTALLATION MODE                              #
echo    ===============================================================================
echo.

REM Use default installation directory
set "INSTALL_DIR=%USERPROFILE%\CAESER_Water_levels_monitoring_system"

echo    [DEBUG] Installation directory: %INSTALL_DIR%
echo    [DEBUG] Current user: %USERNAME%
echo    [DEBUG] System drive: %SystemDrive%
echo.

REM Check if directories exist
if exist "%INSTALL_DIR%" (
    echo    [DEBUG] Found existing installation directory
    echo    [DEBUG] Removing existing installation...
    rmdir /s /q "%INSTALL_DIR%" 2>nul
)

REM Create directories with debug output
echo    [DEBUG] Creating directories...
mkdir "%INSTALL_DIR%" 2>nul && echo    [DEBUG] ✓ Main directory created
mkdir "%INSTALL_DIR%\launchers" 2>nul && echo    [DEBUG] ✓ Launchers directory created
mkdir "%INSTALL_DIR%\databases" 2>nul && echo    [DEBUG] ✓ Databases directory created
mkdir "%INSTALL_DIR%\databases\temp" 2>nul && echo    [DEBUG] ✓ Temp directory created

echo.
echo    [DEBUG] Testing icon file availability...
set "MAIN_ICON=%INSTALL_DIR%\src\gui\icons\water_level_meter.png"
set "VIZ_ICON=%INSTALL_DIR%\src\gui\icons\Water_level_tab_icon.png"

REM Skip full installation for quick debugging - just copy source files
echo    [DEBUG] Copying source files for icon testing...
set "CODE_DIR=%~dp0"
if "%CODE_DIR:~-1%"=="\" set "CODE_DIR=%CODE_DIR:~0,-1%"

xcopy "%CODE_DIR%\src" "%INSTALL_DIR%\src\" /E /I /Y >nul 2>nul
xcopy "%CODE_DIR%\assets" "%INSTALL_DIR%\assets\" /E /I /Y >nul 2>nul

echo    [DEBUG] Checking for icon files...
if exist "%MAIN_ICON%" (
    echo    [DEBUG] ✓ Main app icon found: %MAIN_ICON%
) else (
    echo    [DEBUG] ✗ Main app icon NOT found: %MAIN_ICON%
)

if exist "%VIZ_ICON%" (
    echo    [DEBUG] ✓ Visualizer icon found: %VIZ_ICON%
) else (
    echo    [DEBUG] ✗ Visualizer icon NOT found: %VIZ_ICON%
)

echo.
echo    [DEBUG] Testing different icon approaches...

REM Test different icon methods
echo    [DEBUG] Method 1: Testing imageres.dll icons...
powershell -ExecutionPolicy Bypass -Command "Write-Host '[DEBUG] Available imageres.dll icons:'; for ($i=1; $i -le 10; $i++) { Write-Host \"Icon $i available\" }"

echo.
echo    [DEBUG] Method 2: Testing system shell32.dll icons...
powershell -ExecutionPolicy Bypass -Command "Write-Host '[DEBUG] Shell32.dll location:'; Write-Host (Test-Path 'C:\Windows\System32\shell32.dll')"

echo.
echo    [DEBUG] Creating test shortcuts with multiple icon methods...

REM Test shortcut 1 - Current method
echo    [DEBUG] Test 1: imageres.dll method...
powershell -ExecutionPolicy Bypass -Command "try { $WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%INSTALL_DIR%\TEST1_imageres.lnk'); $Shortcut.TargetPath = 'notepad.exe'; $Shortcut.IconLocation = 'C:\Windows\System32\imageres.dll, 1'; $Shortcut.Save(); Write-Host '[DEBUG] ✓ Test1 shortcut created with imageres.dll,1' } catch { Write-Host '[DEBUG] ✗ Test1 failed:' $_.Exception.Message }"

REM Test shortcut 2 - Shell32 method
echo    [DEBUG] Test 2: shell32.dll method...
powershell -ExecutionPolicy Bypass -Command "try { $WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%INSTALL_DIR%\TEST2_shell32.lnk'); $Shortcut.TargetPath = 'notepad.exe'; $Shortcut.IconLocation = 'C:\Windows\System32\shell32.dll, 3'; $Shortcut.Save(); Write-Host '[DEBUG] ✓ Test2 shortcut created with shell32.dll,3' } catch { Write-Host '[DEBUG] ✗ Test2 failed:' $_.Exception.Message }"

REM Test shortcut 3 - Different imageres index
echo    [DEBUG] Test 3: Different imageres index...
powershell -ExecutionPolicy Bypass -Command "try { $WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%INSTALL_DIR%\TEST3_chart.lnk'); $Shortcut.TargetPath = 'notepad.exe'; $Shortcut.IconLocation = 'C:\Windows\System32\imageres.dll, 178'; $Shortcut.Save(); Write-Host '[DEBUG] ✓ Test3 shortcut created with imageres.dll,178' } catch { Write-Host '[DEBUG] ✗ Test3 failed:' $_.Exception.Message }"

REM Test shortcut 4 - Computer/monitoring icon
echo    [DEBUG] Test 4: Computer/monitoring icon...
powershell -ExecutionPolicy Bypass -Command "try { $WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%INSTALL_DIR%\TEST4_computer.lnk'); $Shortcut.TargetPath = 'notepad.exe'; $Shortcut.IconLocation = 'C:\Windows\System32\imageres.dll, 109'; $Shortcut.Save(); Write-Host '[DEBUG] ✓ Test4 shortcut created with imageres.dll,109' } catch { Write-Host '[DEBUG] ✗ Test4 failed:' $_.Exception.Message }"

echo.
echo    [DEBUG] Creating test VBScript launcher...

REM Create a simple test VBScript to debug app launching
(
    echo Set objShell = CreateObject^("WScript.Shell"^)
    echo WScript.Echo "DEBUG: VBScript starting..."
    echo objShell.CurrentDirectory = "%INSTALL_DIR%"
    echo WScript.Echo "DEBUG: Working directory set to: " ^& objShell.CurrentDirectory
    echo Set objEnv = objShell.Environment^("Process"^)
    echo WScript.Echo "DEBUG: Setting environment variables..."
    echo objEnv^("PATH"^) = "%INSTALL_DIR%\venv\Scripts;" ^& objEnv^("PATH"^)
    echo objEnv^("PYTHONPATH"^) = "%INSTALL_DIR%\venv\Lib\site-packages"
    echo WScript.Echo "DEBUG: PATH updated: " ^& objEnv^("PATH"^)
    echo WScript.Echo "DEBUG: About to launch Python application..."
    echo On Error Resume Next
    echo objShell.Run """%INSTALL_DIR%\venv\Scripts\pythonw.exe"" ""%INSTALL_DIR%\main.py""", 0, True
    echo If Err.Number ^<^> 0 Then
    echo     WScript.Echo "DEBUG: Error launching app: " ^& Err.Description
    echo Else
    echo     WScript.Echo "DEBUG: App launched successfully"
    echo End If
) > "%INSTALL_DIR%\test_launcher_debug.vbs"

echo    [DEBUG] Test launcher created: test_launcher_debug.vbs

echo.
echo    ===============================================================================
echo    #                        DEBUG INSTALLATION COMPLETE                         #
echo    ===============================================================================
echo.
echo    [DEBUG] Installation directory: %INSTALL_DIR%
echo.
echo    [DEBUG] Test files created:
echo        [*] TEST1_imageres.lnk (imageres.dll, icon 1)
echo        [*] TEST2_shell32.lnk (shell32.dll, icon 3) 
echo        [*] TEST3_chart.lnk (imageres.dll, icon 178)
echo        [*] TEST4_computer.lnk (imageres.dll, icon 109)
echo        [*] test_launcher_debug.vbs (app launcher with logging)
echo.
echo    [DEBUG] To test icons:
echo        1. Check which TEST shortcuts show proper icons
echo        2. Note the icon numbers that work
echo.
echo    [DEBUG] To test app launcher:
echo        1. Double-click test_launcher_debug.vbs
echo        2. Check for debug messages showing what fails
echo.
echo    [DEBUG] Opening installation folder for inspection...
start "" "%INSTALL_DIR%"
echo.
pause

endlocal