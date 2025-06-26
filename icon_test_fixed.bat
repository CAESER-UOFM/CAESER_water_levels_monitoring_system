@echo off
echo ================================================================
echo                FIXED ICON TEST FOR WINDOWS 10
================================================================
echo.

set "TEST_DIR=%USERPROFILE%\Desktop\IconTestFixed"
mkdir "%TEST_DIR%" 2>nul

echo Testing on Windows 10 Build 22631...
echo.

REM Test 1: VBScript method (more reliable than PowerShell)
echo [1] Testing VBScript method...
(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = "%TEST_DIR%\VBScript_Test.lnk"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "notepad.exe"
echo oLink.IconLocation = "C:\Windows\System32\shell32.dll,3"
echo oLink.Save
echo WScript.Echo "VBScript shortcut created"
) > "%TEST_DIR%\create_shortcut.vbs"

cscript //nologo "%TEST_DIR%\create_shortcut.vbs"

REM Test 2: Different shell32 icon
echo [2] Testing different shell32 icon...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Shell32_Icon2.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\System32\shell32.dll,2'; $s.Save()"

REM Test 3: Notepad's own icon
echo [3] Testing notepad's own icon...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Notepad_Icon.lnk'); $s.TargetPath = 'C:\Windows\System32\notepad.exe'; $s.IconLocation = 'C:\Windows\System32\notepad.exe,0'; $s.Save()"

REM Test 4: Explorer icon
echo [4] Testing explorer icon...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Explorer_Icon.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\explorer.exe,0'; $s.Save()"

REM Test 5: System icon without index
echo [5] Testing without icon index...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\No_Index.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\System32\shell32.dll'; $s.Save()"

echo.
echo ================================================================
echo Created test shortcuts. Check which ones show actual icons:
echo.
echo   VBScript_Test.lnk   - VBScript created (shell32.dll,3)
echo   Shell32_Icon2.lnk   - PowerShell (shell32.dll,2)  
echo   Notepad_Icon.lnk    - Notepad's own icon
echo   Explorer_Icon.lnk   - Windows Explorer icon
echo   No_Index.lnk        - No index number
echo.
echo ================================================================
echo.
echo ALSO TEST MANUALLY:
echo 1. Right-click Desktop > New > Shortcut
echo 2. Target: notepad.exe
echo 3. Right-click shortcut > Properties > Change Icon
echo 4. Pick any icon and note what format works!
echo.

start "" "%TEST_DIR%"
pause