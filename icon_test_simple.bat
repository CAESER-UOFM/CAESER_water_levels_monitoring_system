@echo off
echo ================================================================
echo                    SIMPLE ICON TEST
echo ================================================================
echo.
echo This will create test shortcuts with different icon methods
echo to find what actually works on Windows.
echo.

set "TEST_DIR=%USERPROFILE%\Desktop\IconTest"
mkdir "%TEST_DIR%" 2>nul

echo Creating test shortcuts on Desktop...
echo.

REM Test 1: Direct system icon reference
echo [1] Testing system icon (shell32.dll index 3)...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Test1_System.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'shell32.dll,3'; $s.Save(); Write-Host 'Created Test1_System.lnk'"

REM Test 2: Full path system icon
echo [2] Testing full path system icon...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Test2_FullPath.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\System32\shell32.dll,4'; $s.Save(); Write-Host 'Created Test2_FullPath.lnk'"

REM Test 3: imageres.dll icon
echo [3] Testing imageres.dll icon...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Test3_Imageres.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\System32\imageres.dll,109'; $s.Save(); Write-Host 'Created Test3_Imageres.lnk'"

REM Test 4: Different imageres icon
echo [4] Testing different imageres icon...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Test4_Chart.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\System32\imageres.dll,178'; $s.Save(); Write-Host 'Created Test4_Chart.lnk'"

REM Test 5: No space after comma
echo [5] Testing no space after comma...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Test5_NoSpace.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\System32\imageres.dll,1'; $s.Save(); Write-Host 'Created Test5_NoSpace.lnk'"

REM Test 6: Explorer icon
echo [6] Testing Windows Explorer icon...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Test6_Explorer.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\explorer.exe,0'; $s.Save(); Write-Host 'Created Test6_Explorer.lnk'"

echo.
echo ================================================================
echo Test shortcuts created in: %TEST_DIR%
echo.
echo Please check each shortcut to see which ones show proper icons:
echo   Test1_System.lnk     - shell32.dll,3
echo   Test2_FullPath.lnk   - full path shell32.dll,4  
echo   Test3_Imageres.lnk   - imageres.dll,109
echo   Test4_Chart.lnk      - imageres.dll,178
echo   Test5_NoSpace.lnk    - imageres.dll,1 (no space)
echo   Test6_Explorer.lnk   - explorer.exe,0
echo.
echo Tell me which TEST shows a proper icon (not generic)!
echo ================================================================
echo.

start "" "%TEST_DIR%"
pause