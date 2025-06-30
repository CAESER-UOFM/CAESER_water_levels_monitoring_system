@echo off
echo ================================================================
echo          TESTING MUN FILES (CONFIRMED SOLUTION)
================================================================
echo.
echo Based on internet research: Modern Windows stores icons in .mun files
echo not in .dll files anymore!
echo.

set "TEST_DIR=%USERPROFILE%\Desktop\MunTest"
mkdir "%TEST_DIR%" 2>nul

echo [DEBUG] Checking if .mun files exist...
if exist "C:\Windows\SystemResources\shell32.dll.mun" (
    echo ✓ shell32.dll.mun exists - REAL icons are here!
) else (
    echo ✗ shell32.dll.mun NOT found
)

if exist "C:\Windows\SystemResources\imageres.dll.mun" (
    echo ✓ imageres.dll.mun exists - REAL icons are here!
) else (
    echo ✗ imageres.dll.mun NOT found
)

echo.
echo [TEST 1] Using .mun files instead of .dll files...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\MUN_Test1.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\SystemResources\shell32.dll.mun,3'; $s.Save(); Write-Host 'MUN test 1 created'"

echo [TEST 2] Different MUN icon...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\MUN_Test2.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\SystemResources\imageres.dll.mun,109'; $s.Save(); Write-Host 'MUN test 2 created'"

echo [TEST 3] Alternative - Use actual executable icons...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\EXE_Test.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\System32\notepad.exe,0'; $s.Save(); Write-Host 'EXE test created'"

echo [TEST 4] Use calc.exe icon...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\CALC_Test.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\System32\calc.exe,0'; $s.Save(); Write-Host 'CALC test created'"

echo.
echo ================================================================
echo Internet research shows Windows 10+ moved icons to .mun files!
echo.
echo Check these test shortcuts:
echo   MUN_Test1.lnk   - shell32.dll.mun,3
echo   MUN_Test2.lnk   - imageres.dll.mun,109  
echo   EXE_Test.lnk    - notepad.exe,0 (executable icon)
echo   CALC_Test.lnk   - calc.exe,0 (calculator icon)
echo.
echo If MUN files work, we found the solution!
echo If EXE files work, we use executable icons instead!
echo ================================================================

start "" "%TEST_DIR%"
pause