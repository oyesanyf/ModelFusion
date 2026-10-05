@echo off
setlocal enabledelayedexpansion

REM =========================================================================
REM ModelFusion Universal MCP Server Launcher
REM Runs ModelFusion Master CLI in Model Context Protocol (MCP) stdio mode
REM =========================================================================

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..\..

REM 1. Discover ModelFusion Master CLI Binary
set CLI_BIN=
if exist "%REPO_ROOT%\mcp\bin\climcp.exe" (
    set "CLI_BIN=%REPO_ROOT%\mcp\bin\climcp.exe"
) else if exist "%REPO_ROOT%\target\release\climcp.exe" (
    set "CLI_BIN=%REPO_ROOT%\target\release\climcp.exe"
) else if exist "%LOCALAPPDATA%\HugOS MCP\bin\climcp.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS MCP\bin\climcp.exe"
) else if exist "%REPO_ROOT%\mcp\bin\cli.exe" (
    set "CLI_BIN=%REPO_ROOT%\mcp\bin\cli.exe"
) else if exist "%LOCALAPPDATA%\HugOS MCP\bin\cli.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS MCP\bin\cli.exe"
) else if exist "%REPO_ROOT%\target\release\cli.exe" (
    set "CLI_BIN=%REPO_ROOT%\target\release\cli.exe"
) else if exist "%REPO_ROOT%\IDE\bin\cliide.exe" (
    set "CLI_BIN=%REPO_ROOT%\IDE\bin\cliide.exe"
) else if exist "%REPO_ROOT%\IDE\bin\cli.exe" (
    set "CLI_BIN=%REPO_ROOT%\IDE\bin\cli.exe"
) else if exist "%LOCALAPPDATA%\HugOS IDE\bin\cliide.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS IDE\bin\cliide.exe"
) else if exist "%LOCALAPPDATA%\HugOS IDE\bin\cli.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS IDE\bin\cli.exe"
) else if exist "%REPO_ROOT%\browser\bin\clibrowser.exe" (
    set "CLI_BIN=%REPO_ROOT%\browser\bin\clibrowser.exe"
) else if exist "%LOCALAPPDATA%\HugOS Browser\bin\clibrowser.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS Browser\bin\clibrowser.exe"
) else if exist "%LOCALAPPDATA%\HugOS Browser\bin\cli.exe" (
    set "CLI_BIN=%LOCALAPPDATA%\HugOS Browser\bin\cli.exe"
) else if exist "%REPO_ROOT%\browser\bin\cli.exe" (
    set "CLI_BIN=%REPO_ROOT%\browser\bin\cli.exe"
) else (
    where climcp.exe >nul 2>&1
    if not errorlevel 1 (
        set "CLI_BIN=climcp.exe"
    ) else (
        where cli.exe >nul 2>&1
        if not errorlevel 1 (
            set "CLI_BIN=cli.exe"
        ) else (
            where cliide.exe >nul 2>&1
            if not errorlevel 1 (
                set "CLI_BIN=cliide.exe"
            )
        )
    )
)

if "%CLI_BIN%"=="" (
    echo [ERROR] ModelFusion Master CLI (climcp.exe / cli.exe) not found! >&2
    echo [INFO] Please compile with 'cargo build --release --bin cli' or install HugOS MCP / IDE. >&2
    exit /b 1
)

REM 2. Discover Database Path (optional)
set DB_ARG=
if exist "%REPO_ROOT%\IDE\db\hf_models.db" (
    set "DB_ARG=--db-path ""%REPO_ROOT%\IDE\db\hf_models.db"""
) else if exist "%LOCALAPPDATA%\HugOS IDE\db\hf_models.db" (
    set "DB_ARG=--db-path ""%LOCALAPPDATA%\HugOS IDE\db\hf_models.db"""
)

REM 3. Launch MCP Stdio Server
if "%DB_ARG%"=="" (
    "%CLI_BIN%" --mcp %*
) else (
    "%CLI_BIN%" --mcp %DB_ARG% %*
)
