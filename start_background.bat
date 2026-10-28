@echo off
REM Battery Monitor Pro - Silent Background Launcher
REM Double-click this script to start the app in the background without keeping a terminal open.

start "" pythonw "%~dp0src\app_launcher.pyw" --service
if %ERRORLEVEL% NEQ 0 (
    start "" python "%~dp0src\app_launcher.py"
)
