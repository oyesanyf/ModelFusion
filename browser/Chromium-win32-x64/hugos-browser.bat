@echo off
setlocal enabledelayedexpansion

REM =========================================================================
REM HugOS Intelligent Chromium Browser Launcher
REM Launches Chromium with Remote Debugging (port 9222) and HugOS AI Extension
REM =========================================================================

set SCRIPT_DIR=%~dp0
set EXTENSION_DIR=%SCRIPT_DIR%..\extension
for %%i in ("%EXTENSION_DIR%") do set EXTENSION_PATH=%%~fi

set USER_DATA_DIR=%LOCALAPPDATA%\HugOS Browser\User Data
if not exist "%USER_DATA_DIR%" mkdir "%USER_DATA_DIR%"

REM 1. Search for local or installed Chromium / Chrome / Edge binary
set CHROME_BIN=

if exist "%SCRIPT_DIR%chrome.exe" (
    set "CHROME_BIN=%SCRIPT_DIR%chrome.exe"
) else if exist "%SCRIPT_DIR%chromium.exe" (
    set "CHROME_BIN=%SCRIPT_DIR%chromium.exe"
) else if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_BIN=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
) else if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_BIN=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
) else if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_BIN=%LocalAppData%\Google\Chrome\Application\chrome.exe"
) else if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    set "CHROME_BIN=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
) else if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    set "CHROME_BIN=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
)

if "%CHROME_BIN%"=="" (
    echo [ERROR] No compatible Chromium, Google Chrome, or Microsoft Edge executable found.
    echo Please install Google Chrome or place chrome.exe in %SCRIPT_DIR%
    pause
    exit /b 1
)

echo [START] Launching HugOS Browser Engine...
echo [INFO] Binary: "%CHROME_BIN%"
echo [INFO] Remote Debugging Port: 9222
echo [INFO] Extension Path: "%EXTENSION_PATH%"
echo [INFO] User Data Dir: "%USER_DATA_DIR%"

start "" "%CHROME_BIN%" ^
    --remote-debugging-port=9222 ^
    --load-extension="%EXTENSION_PATH%" ^
    --user-data-dir="%USER_DATA_DIR%" ^
    --disable-backgrounding-occluded-windows ^
    --no-first-run ^
    --no-default-browser-check ^
    --enable-features=SidePanel,SidePanelPinning ^
    https://huggingface.co/models

endlocal
