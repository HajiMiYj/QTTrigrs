@echo off
rem ===========================================================================
rem  Build the QTTrigrs installer with Inno Setup 6.
rem  Run build_installer.cmd (or double-click it).
rem  Output: ..\dist\installer\QTTrigrs-1.0.0-setup.exe
rem ===========================================================================
setlocal
cd /d "%~dp0"

set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo [ERROR] Inno Setup 6 not found. Install it, or edit ISCC= in this file.
  exit /b 1
)

if not exist "..\dist\main.dist\QTTrigrs.exe" (
  echo [ERROR] Packaged app not found: ..\dist\main.dist\QTTrigrs.exe
  echo         Run this first:   python build_nuitka.py
  exit /b 1
)

echo [1/1] Compiling installer ...
"%ISCC%" "QTTrigrs.iss"
if errorlevel 1 (
  echo [ERROR] Compile failed. See the messages above.
  exit /b 1
)

echo.
echo Done. Installer is in ..\dist\installer\
for %%F in ("..\dist\installer\*.exe") do echo   %%~nxF
endlocal
