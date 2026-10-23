@echo off
setlocal enabledelayedexpansion

REM =========================================================================
REM HugOS Intelligent Chromium Browser Launcher
REM Instant Launch (<100ms): Shows instant splash, spawns or focuses Chromium GUI
REM on Step 1, then performs non-blocking background daemon startup in Step 2.
REM =========================================================================

set SCRIPT_DIR=%~dp0
if exist "%SCRIPT_DIR%hugos-splash.hta" (
    start "" mshta.exe "%SCRIPT_DIR%hugos-splash.hta"
)

REM -------------------------------------------------------------------------
REM Step 1: Instant Browser Window Launch (Zero Blocking Delays)
REM -------------------------------------------------------------------------
set CLI_BIN=
if exist "%SCRIPT_DIR%..\bin\clibrowser.exe" (
    set "CLI_BIN=%SCRIPT_DIR%..\bin\clibrowser.exe"
) else if exist "%LOCALAPPDATA%\HugOS Browser\bin\clibrowser.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS Browser\bin\clibrowser.exe"
) else if exist "%SCRIPT_DIR%..\..\target\release\clibrowser.exe" (
    set "CLI_BIN=%SCRIPT_DIR%..\..\target\release\clibrowser.exe"
) else if exist "%SCRIPT_DIR%..\bin\cli.exe" (
    set "CLI_BIN=%SCRIPT_DIR%..\bin\cli.exe"
) else if exist "%LOCALAPPDATA%\HugOS Browser\bin\cli.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS Browser\bin\cli.exe"
) else if exist "%SCRIPT_DIR%..\..\target\release\cli.exe" (
    set "CLI_BIN=%SCRIPT_DIR%..\..\target\release\cli.exe"
) else if exist "D:\harfile\ModelFusion\target\release\clibrowser.exe" (
    set "CLI_BIN=D:\harfile\ModelFusion\target\release\clibrowser.exe"
) else if exist "D:\harfile\ModelFusion\target\release\cli.exe" (
    set "CLI_BIN=D:\harfile\ModelFusion\target\release\cli.exe"
)

set EXTENSION_DIR=%SCRIPT_DIR%..\extension
for %%i in ("%EXTENSION_DIR%") do set EXTENSION_PATH=%%~fi

set "DEFAULT_HOME=%SCRIPT_DIR%..\ui\index.html"
if not exist "%DEFAULT_HOME%" (
    if exist "%LOCALAPPDATA%\HugOS Browser\ui\index.html" (
        set "DEFAULT_HOME=%LOCALAPPDATA%\HugOS Browser\ui\index.html"
    )
)
for %%i in ("%DEFAULT_HOME%") do set "HOME_FILE_PATH=%%~fi"

REM Determine Startup URL (always genuine HugOS Browser UI via file:/// protocol)
set "START_URL=file:///%HOME_FILE_PATH:\=/%"
set "HAS_CUSTOM_URL=0"
if not "%~1"=="" (
    set "START_URL=%~1"
    set "HAS_CUSTOM_URL=1"
)

set USER_DATA_DIR=%LOCALAPPDATA%\HugOS Browser\User Data
if not exist "%USER_DATA_DIR%" mkdir "%USER_DATA_DIR%"

set ALREADY_OPEN=0
if not "%CLI_BIN%"=="" (
    if "%HAS_CUSTOM_URL%"=="0" (
        "%CLI_BIN%" --check-browser-window >nul 2>&1
        if !errorlevel! equ 0 set ALREADY_OPEN=1
    )
)

REM Search for local or installed Chromium / Chrome / Edge binary
set CHROME_BIN=
if exist "%SCRIPT_DIR%chrome.exe" (
    set "CHROME_BIN=%SCRIPT_DIR%chrome.exe"
) else if exist "%SCRIPT_DIR%chromium.exe" (
    set "CHROME_BIN=%SCRIPT_DIR%chromium.exe"
) else if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_BIN=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
) else if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_BIN=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_BIN=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) else if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    set "CHROME_BIN=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
) else if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    set "CHROME_BIN=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
)

if "%CHROME_BIN%"=="" (
    echo [ERROR] No Chromium/Chrome/Edge engine found.
    exit /b 1
)

if "%ALREADY_OPEN%"=="0" (
    start "" "%CHROME_BIN%" --app="%START_URL%" --remote-debugging-port=9222 --remote-allow-origins=* --load-extension="%EXTENSION_PATH%" --user-data-dir="%USER_DATA_DIR%" --enable-gpu-rasterization --enable-zero-copy --ignore-gpu-blocklist --disable-renderer-backgrounding --disable-background-timer-throttling --enable-smooth-scrolling --disable-backgrounding-occluded-windows --no-first-run --no-default-browser-check --enable-features=SidePanel,SidePanelPinning,CanvasOopRasterization --disable-features=Translate,OptimizationHints --disk-cache-size=104857600
)

REM -------------------------------------------------------------------------
REM Step 2: Non-Blocking Foreground Promotion & Background Daemon Startup
REM Spawns hidden via run_hidden.vbs after instant launch, with fast health checks
REM on http://127.0.0.1:5000/health and fallback http://127.0.0.1:5005/health.
REM -------------------------------------------------------------------------
set "OLLAMA_ORIGINS=*"
if not "%CLI_BIN%"=="" (
    wscript.exe //B //nologo "%SCRIPT_DIR%run_hidden.vbs" "%CLI_BIN%" "--focus-browser"
    wscript.exe //B //nologo "%SCRIPT_DIR%run_hidden.vbs" "%CLI_BIN%" "--ensure-ollama"
    curl -s -f --connect-timeout 1 --max-time 1 http://127.0.0.1:5000/health | findstr /i "modelfusion" >nul 2>&1
    if !errorlevel! neq 0 (
        curl -s -f --connect-timeout 1 --max-time 1 http://127.0.0.1:5005/health | findstr /i "modelfusion" >nul 2>&1
        if !errorlevel! neq 0 (
            wscript.exe //B //nologo "%SCRIPT_DIR%run_hidden.vbs" "%CLI_BIN%" --server --port 5000
        )
    )
)

endlocal
exit /b 0
