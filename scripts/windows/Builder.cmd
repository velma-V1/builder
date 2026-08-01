@echo off
rem Builder desktop-shortcut entrypoint (Phase 3A). Double-click target: this file.
rem Thin wrapper only -- all real logic lives in Builder.ps1 (WSL2/distro checks, then hands
rem off to scripts/start_all.py inside WSL for everything else).

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Builder.ps1"
set BUILDER_EXIT_CODE=%ERRORLEVEL%

if not "%BUILDER_EXIT_CODE%"=="0" (
    echo.
    echo Builder did not start successfully. Press any key to close this window.
    pause >nul
)

exit /b %BUILDER_EXIT_CODE%
