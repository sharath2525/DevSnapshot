@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE="
set "PYTHON_ARGS="

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        for /f "delims=" %%I in ('where py 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%I"
        set "PYTHON_ARGS=-3"
    ) else (
        where python >nul 2>nul
        if not errorlevel 1 for /f "delims=" %%I in ('where python 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%I"
    )
)

if not defined PYTHON_EXE (
    echo Python 3 was not found.
    echo Install Python 3 for Windows or create .venv in this folder, then run build.bat again.
    exit /b 1
)

echo Installing build requirements...
"%PYTHON_EXE%" %PYTHON_ARGS% -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 exit /b 1

echo Running offline unit tests...
"%PYTHON_EXE%" %PYTHON_ARGS% -m unittest discover -s tests -v
if errorlevel 1 exit /b 1

echo Verifying Qt with an isolated Windows runtime path...
set "ORIGINAL_PATH=%PATH%"
set "PATH=%SystemRoot%\System32;%SystemRoot%;%SystemRoot%\System32\Wbem;%SystemRoot%\System32\WindowsPowerShell\v1.0\;%SystemRoot%\System32\OpenSSH\"
"%PYTHON_EXE%" %PYTHON_ARGS% -c "from PySide6 import QtCore, QtGui, QtWidgets; print('Qt runtime check: OK', QtCore.qVersion())"
if errorlevel 1 (
    set "PATH=%ORIGINAL_PATH%"
    exit /b 1
)

echo Building DevSnapshot.exe in an isolated environment...
"%PYTHON_EXE%" %PYTHON_ARGS% -m PyInstaller --clean --noconfirm DevSnapshot.spec
if errorlevel 1 (
    set "PATH=%ORIGINAL_PATH%"
    exit /b 1
)

if not exist "dist\DevSnapshot.exe" (
    echo Build completed without the expected dist\DevSnapshot.exe output.
    set "PATH=%ORIGINAL_PATH%"
    exit /b 1
)

echo Testing the packaged executable with the normal Windows Qt platform...
set "DEVSNAPSHOT_SMOKE_TEST=1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$p = Start-Process -FilePath (Join-Path $pwd 'dist\DevSnapshot.exe') -PassThru -WindowStyle Hidden; if (-not $p.WaitForExit(15000)) { & taskkill.exe /PID $p.Id /T /F | Out-Null; Write-Error 'Packaged executable did not exit after its startup smoke test.'; exit 1 }; if ($p.ExitCode -ne 0) { Write-Error ('Packaged executable exited with code ' + $p.ExitCode); exit 1 }; Write-Host 'Packaged executable startup test: OK'"
set "SMOKE_RESULT=%ERRORLEVEL%"
set "DEVSNAPSHOT_SMOKE_TEST="
set "PATH=%ORIGINAL_PATH%"
if not "%SMOKE_RESULT%"=="0" exit /b %SMOKE_RESULT%

echo.
echo Build complete: %CD%\dist\DevSnapshot.exe
exit /b 0
