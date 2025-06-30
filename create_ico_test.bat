@echo off
echo ================================================================
echo              TESTING WITH ACTUAL ICO FILES
================================================================
echo.

set "TEST_DIR=%USERPROFILE%\Desktop\IcoTest"
mkdir "%TEST_DIR%" 2>nul

echo Creating a simple ICO file from PNG...
echo.

REM Create a simple VBScript to convert PNG to ICO using Windows APIs
(
echo Option Explicit
echo.
echo Dim fso, shell
echo Set fso = CreateObject^("Scripting.FileSystemObject"^)
echo Set shell = CreateObject^("WScript.Shell"^)
echo.
echo ' Try to find an existing ICO file in Windows
echo Dim icoPath
echo icoPath = "C:\Windows\System32\user32.dll"
echo.
echo ' Create test shortcut with ICO file
echo Dim shortcut
echo Set shortcut = shell.CreateShortcut^("%TEST_DIR%\TestWithICO.lnk"^)
echo shortcut.TargetPath = "notepad.exe"
echo shortcut.IconLocation = icoPath ^& ",0"
echo shortcut.Save
echo.
echo WScript.Echo "Created shortcut with ICO reference"
echo.
echo ' Also try creating one without any icon specification
echo Set shortcut = shell.CreateShortcut^("%TEST_DIR%\NoIconSet.lnk"^)
echo shortcut.TargetPath = "notepad.exe"
echo shortcut.Save
echo WScript.Echo "Created shortcut with no icon set"
) > "%TEST_DIR%\test_ico.vbs"

cscript //nologo "%TEST_DIR%\test_ico.vbs"

echo.
echo Now let's test the MANUAL approach...
echo.
echo MANUAL TEST INSTRUCTIONS:
echo 1. Right-click on Desktop
echo 2. New ^> Shortcut
echo 3. Type: notepad.exe
echo 4. Name it: ManualTest
echo 5. Right-click the new shortcut ^> Properties
echo 6. Click "Change Icon..." button
echo 7. Browse and pick ANY icon that shows up
echo 8. Click OK
echo.
echo THEN tell me:
echo - Did the manual shortcut show a custom icon?
echo - What file path did Windows use when you picked an icon?
echo.

echo ================================================================
echo Key Question: Can you MANUALLY set icons in Windows 10?
echo If manual doesn't work, Windows has icon restrictions enabled.
echo ================================================================

start "" "%TEST_DIR%"
pause