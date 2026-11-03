@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py electrical.py %*
) else (
    python electrical.py %*
)
