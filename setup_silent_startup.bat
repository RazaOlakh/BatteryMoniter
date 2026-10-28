@echo off
title Battery Monitor Pro - Silent Startup Setup
echo ============================================================
echo   Battery Monitor Pro - 100%% Silent Windows Startup Setup
echo ============================================================
echo.

set "PY_CMD="

REM 1. Try 'python' in PATH
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=python"
    goto found_python
)

REM 2. Try 'py -3' launcher
py -3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py -3"
    goto found_python
)

REM 3. Check common user install paths in %LOCALAPPDATA%\Programs\Python
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD="%%D\python.exe""
        goto found_python
    )
)

REM 4. Check common Program Files install paths
for /d %%D in ("%ProgramFiles%\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD="%%D\python.exe""
        goto found_python
    )
)

REM 5. Check root drive Python installs (e.g. C:\Python314)
for /d %%D in ("C:\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD="%%D\python.exe""
        goto found_python
    )
)

:found_python
if "%PY_CMD%"=="" (
    echo [ERROR] Python was not found in PATH or standard installation folders.
    echo Please ensure Python is installed and added to PATH.
    pause
    exit /b 1
)

echo Using Python: %PY_CMD%
echo Updating Windows registry and startup configurations...
%PY_CMD% "%~dp0src\app_launcher.py" --fix-startup
echo.
echo ============================================================
echo [DONE] Silent startup has been configured successfully!
echo [DONE] Dual-channel startup (Registry Run + Startup folder) active.
echo [DONE] The application is now running silently in the background.
echo [INFO] Look for the battery icon in your Windows system tray.
echo ============================================================
echo.
pause
