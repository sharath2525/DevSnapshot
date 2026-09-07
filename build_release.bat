@echo off
setlocal
cd /d "%~dp0"

call build.bat
if errorlevel 1 exit /b 1

set "ISCC_EXE="
where ISCC.exe >nul 2>nul
if not errorlevel 1 for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC_EXE set "ISCC_EXE=%%I"
if not defined ISCC_EXE if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if not defined ISCC_EXE (
    echo Inno Setup 6 was not found.
    echo Install it from https://jrsoftware.org/isdl.php and run build_release.bat again.
    exit /b 1
)

echo Building the signed-ready per-user installer...
for /f "usebackq delims=" %%V in (`powershell.exe -NoProfile -Command "(Get-Item 'dist\DevSnapshot.exe').VersionInfo.ProductVersion"`) do set "APP_VERSION=%%V"
if not defined APP_VERSION (
    echo Could not read the application version from dist\DevSnapshot.exe.
    exit /b 1
)
"%ISCC_EXE%" /DMyAppVersion="%APP_VERSION%" "installer\DevSnapshot.iss"
if errorlevel 1 exit /b 1

echo.
echo Release artifacts:
echo   %CD%\dist\DevSnapshot.exe
echo   %CD%\dist\installer\DevSnapshot-Setup-%APP_VERSION%.exe
exit /b 0
