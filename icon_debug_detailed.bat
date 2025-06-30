@echo off
echo ================================================================
echo              DETAILED ICON DEBUGGING
================================================================
echo.

set "TEST_DIR=%USERPROFILE%\Desktop\IconDebug"
mkdir "%TEST_DIR%" 2>nul

echo [DEBUG] Windows Version:
ver
echo.

echo [DEBUG] Checking if icon files exist...
if exist "C:\Windows\System32\shell32.dll" (
    echo ✓ shell32.dll exists
) else (
    echo ✗ shell32.dll NOT found
)

if exist "C:\Windows\System32\imageres.dll" (
    echo ✓ imageres.dll exists
) else (
    echo ✗ imageres.dll NOT found
)

if exist "C:\Windows\explorer.exe" (
    echo ✓ explorer.exe exists
) else (
    echo ✗ explorer.exe NOT found
)

echo.
echo [DEBUG] Testing PowerShell shortcut creation with error handling...

REM Test with detailed error reporting
powershell -Command "
try {
    Write-Host '[DEBUG] Creating WScript.Shell object...'
    $ws = New-Object -ComObject WScript.Shell
    Write-Host '[DEBUG] ✓ WScript.Shell created'
    
    Write-Host '[DEBUG] Creating shortcut object...'
    $shortcut = $ws.CreateShortcut('%TEST_DIR%\DetailedTest.lnk')
    Write-Host '[DEBUG] ✓ Shortcut object created'
    
    Write-Host '[DEBUG] Setting target path...'
    $shortcut.TargetPath = 'notepad.exe'
    Write-Host '[DEBUG] ✓ Target path set'
    
    Write-Host '[DEBUG] Setting icon location...'
    $shortcut.IconLocation = 'C:\Windows\System32\shell32.dll,3'
    Write-Host '[DEBUG] ✓ Icon location set'
    
    Write-Host '[DEBUG] Saving shortcut...'
    $shortcut.Save()
    Write-Host '[DEBUG] ✓ Shortcut saved'
    
    Write-Host '[DEBUG] Reading back shortcut properties...'
    $readBack = $ws.CreateShortcut('%TEST_DIR%\DetailedTest.lnk')
    Write-Host '[DEBUG] Target:' $readBack.TargetPath
    Write-Host '[DEBUG] Icon:' $readBack.IconLocation
    Write-Host '[DEBUG] Working Dir:' $readBack.WorkingDirectory
} catch {
    Write-Host '[ERROR] Exception occurred:'
    Write-Host $_.Exception.Message
    Write-Host $_.Exception.GetType().FullName
}"

echo.
echo [DEBUG] Testing alternative icon methods...

REM Test 1: Try without path
echo [TEST 1] No path, just filename...
powershell -Command "try { $ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Test1_NoPath.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'shell32.dll,3'; $s.Save(); Write-Host 'Test1 created' } catch { Write-Host 'Test1 failed:' $_.Exception.Message }"

REM Test 2: Try system32 path
echo [TEST 2] System32 path...
powershell -Command "try { $ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Test2_Sys32.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = '%%SystemRoot%%\System32\shell32.dll,3'; $s.Save(); Write-Host 'Test2 created' } catch { Write-Host 'Test2 failed:' $_.Exception.Message }"

REM Test 3: Try quotes around path
echo [TEST 3] Quoted path...
powershell -Command "try { $ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Test3_Quoted.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = '\"C:\Windows\System32\shell32.dll\",3'; $s.Save(); Write-Host 'Test3 created' } catch { Write-Host 'Test3 failed:' $_.Exception.Message }"

REM Test 4: Try different index format
echo [TEST 4] Different index format...
powershell -Command "try { $ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Test4_Index.lnk'); $s.TargetPath = 'notepad.exe'; $s.IconLocation = 'C:\Windows\System32\shell32.dll'; $s.Save(); Write-Host 'Test4 created' } catch { Write-Host 'Test4 failed:' $_.Exception.Message }"

REM Test 5: Try target's own icon
echo [TEST 5] Target program icon...
powershell -Command "try { $ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TEST_DIR%\Test5_Target.lnk'); $s.TargetPath = 'C:\Windows\System32\notepad.exe'; $s.IconLocation = 'C:\Windows\System32\notepad.exe,0'; $s.Save(); Write-Host 'Test5 created' } catch { Write-Host 'Test5 failed:' $_.Exception.Message }"

echo.
echo [DEBUG] Creating reference shortcut manually...
echo [DEBUG] Right-click on Desktop, create shortcut to notepad.exe manually,
echo [DEBUG] then right-click shortcut ^> Properties ^> Change Icon...
echo [DEBUG] See what format Windows uses when YOU set an icon manually.
echo.

echo ================================================================
echo Tests completed! Check folder: %TEST_DIR%
echo.
echo IMPORTANT: Create a manual shortcut and see what icon format works!
echo ================================================================

start "" "%TEST_DIR%"
pause