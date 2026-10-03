@echo off
setlocal enabledelayedexpansion

REM =========================================================================
REM HugOS Intelligent Chromium Browser Launcher
REM Launches Chromium with Remote Debugging (port 9222) and HugOS AI Extension
REM =========================================================================

set SCRIPT_DIR=%~dp0
set EXTENSION_DIR=%SCRIPT_DIR%..\extension
for %%i in ("%EXTENSION_DIR%") do set EXTENSION_PATH=%%~fi

set "DEFAULT_HOME=%SCRIPT_DIR%..\ui\index.html"
if not exist "%DEFAULT_HOME%" (
    if exist "%LOCALAPPDATA%\HugOS Browser\ui\index.html" (
        set "DEFAULT_HOME=%LOCALAPPDATA%\HugOS Browser\ui\index.html"
    )
)
for %%i in ("%DEFAULT_HOME%") do set "HOME_FILE_PATH=%%~fi"

REM 0. Discover ModelFusion Master CLI Binary (Browser Dedicated clibrowser.exe or cli.exe)
set CLI_BIN=
if exist "%SCRIPT_DIR%..\bin\clibrowser.exe" (
    set "CLI_BIN=%SCRIPT_DIR%..\bin\clibrowser.exe"
) else if exist "%LOCALAPPDATA%\HugOS Browser\bin\clibrowser.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS Browser\bin\clibrowser.exe"
) else if exist "%SCRIPT_DIR%..\bin\cli.exe" (
    set "CLI_BIN=%SCRIPT_DIR%..\bin\cli.exe"
) else if exist "%SCRIPT_DIR%..\..\target\release\clibrowser.exe" (
    set "CLI_BIN=%SCRIPT_DIR%..\..\target\release\clibrowser.exe"
) else if exist "%SCRIPT_DIR%..\..\target\release\cli.exe" (
    set "CLI_BIN=%SCRIPT_DIR%..\..\target\release\cli.exe"
) else if exist "%LOCALAPPDATA%\HugOS Browser\bin\cli.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS Browser\bin\cli.exe"
) else if exist "%LOCALAPPDATA%\HugOS IDE\bin\cliide.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS IDE\bin\cliide.exe"
) else if exist "%LOCALAPPDATA%\HugOS IDE\bin\cli.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS IDE\bin\cli.exe"
) else if exist "D:\harfile\ModelFusion\target\release\cli.exe" (
    set "CLI_BIN=D:\harfile\ModelFusion\target\release\cli.exe"
) else if exist "%SCRIPT_DIR%..\..\target\debug\cli.exe" (
    set "CLI_BIN=%SCRIPT_DIR%..\..\target\debug\cli.exe"
) else (
    where clibrowser >nul 2>&1
    if not errorlevel 1 for /f "delims=" %%f in ('where clibrowser') do set "CLI_BIN=%%f"
    if "!CLI_BIN!"=="" (
        where cli >nul 2>&1
        if not errorlevel 1 for /f "delims=" %%f in ('where cli') do set "CLI_BIN=%%f"
    )
)

REM 0a. Check & Auto-start Ollama Local AI Engine with Open CORS
set "OLLAMA_ORIGINS=*"
curl -s -o nul --max-time 2 http://127.0.0.1:11434/api/tags
if errorlevel 1 (
    echo [INFO] Ollama engine not responding. Auto-starting Ollama...
    if not "%CLI_BIN%"=="" (
        wscript.exe //B //nologo "%SCRIPT_DIR%run_hidden.vbs" "%CLI_BIN%" "--ensure-ollama"
    ) else (
        where ollama >nul 2>&1
        if errorlevel 1 (
            echo [INFO] Ollama is not installed. Installing silently in background...
            curl -s -L -o "%TEMP%\OllamaSetup.exe" https://ollama.com/download/OllamaSetup.exe
            wscript.exe //B //nologo "%SCRIPT_DIR%run_hidden.vbs" "%TEMP%\OllamaSetup.exe" "/SILENT" "/NORESTART"
        )
        wscript.exe //B //nologo "%SCRIPT_DIR%run_hidden.vbs" "ollama" "serve"
    )
)

REM 0b. Check & Auto-start ModelFusion Master Server on port 5000
curl -s -o nul --max-time 2 http://127.0.0.1:5000/health
if errorlevel 1 (
    echo [INFO] ModelFusion Master Server offline on port 5000. Auto-starting server...
    if not "%CLI_BIN%"=="" (
        wscript.exe //B //nologo "%SCRIPT_DIR%run_hidden.vbs" "%CLI_BIN%" "--server" "--port" "5000"
        for /L %%i in (1,1,15) do (
            curl -s -o nul --max-time 1 http://127.0.0.1:5000/health
            if not errorlevel 1 goto :server_ready
            timeout /t 1 /nobreak >nul
        )
    )
)
:server_ready

REM 0c. Determine Startup URL (default to Master Server HTTP origin to prevent null CORS)
set "START_URL=http://localhost:5000/index.html"
if not "%~1"=="" (
    set "START_URL=%~1"
)
if "%CLI_BIN%"=="" (
    curl -s -o nul --max-time 2 http://127.0.0.1:5000/health
    if errorlevel 1 (
        if "%START_URL%"=="http://localhost:5000" (
            set "START_URL=file:///%HOME_FILE_PATH:\=/%"
        )
        if "%START_URL%"=="http://localhost:5000/index.html" (
            set "START_URL=file:///%HOME_FILE_PATH:\=/%"
        )
        if "%START_URL%"=="http://127.0.0.1:5000/index.html" (
            set "START_URL=file:///%HOME_FILE_PATH:\=/%"
        )
    )
) else (
    REM When CLI_BIN is present, ensure START_URL defaults to and remains http://localhost:5000/index.html without file:/// fallback
    if "!START_URL:~0,7!"=="file://" (
        set "START_URL=http://localhost:5000/index.html"
    )
    if "!START_URL!"=="%DEFAULT_HOME%" (
        set "START_URL=http://localhost:5000/index.html"
    )
    if "!START_URL!"=="%HOME_FILE_PATH%" (
        set "START_URL=http://localhost:5000/index.html"
    )
)

set USER_DATA_DIR=%LOCALAPPDATA%\HugOS Browser\User Data
if not exist "%USER_DATA_DIR%" mkdir "%USER_DATA_DIR%"
if exist "%USER_DATA_DIR%\Default\Web Applications" (
    rmdir /s /q "%USER_DATA_DIR%\Default\Web Applications" >nul 2>&1
)
if exist "%USER_DATA_DIR%\Default\Favicons" (
    del /f /q "%USER_DATA_DIR%\Default\Favicons*" >nul 2>&1
)

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
echo [INFO] Startup URL: "%START_URL%"

start "" "%CHROME_BIN%" --app="%START_URL%" --remote-debugging-port=9222 --remote-allow-origins=* --load-extension="%EXTENSION_PATH%" --user-data-dir="%USER_DATA_DIR%" --disable-backgrounding-occluded-windows --no-first-run --no-default-browser-check --enable-features=SidePanel,SidePanelPinning

endlocal
