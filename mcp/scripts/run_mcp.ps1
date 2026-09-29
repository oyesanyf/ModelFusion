# ModelFusion Universal MCP Server PowerShell Launcher
# Runs ModelFusion Master CLI in Model Context Protocol (MCP) stdio mode

$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$repoRoot = Split-Path $PSScriptRoot -Parent | Split-Path -Parent

# 1. Discover ModelFusion Master CLI Binary
$cliCandidates = @(
    (Join-Path $repoRoot "target\release\cli.exe"),
    (Join-Path $repoRoot "IDE\bin\cli.exe"),
    "$env:LOCALAPPDATA\HugOS IDE\bin\cli.exe",
    "$env:LOCALAPPDATA\HugOS Browser\bin\cli.exe",
    (Join-Path $repoRoot "browser\bin\cli.exe")
)

$cliBin = $cliCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $cliBin) {
    $cliCommand = Get-Command "cli.exe" -ErrorAction SilentlyContinue
    if ($cliCommand) {
        $cliBin = $cliCommand.Source
    }
}

if (-not $cliBin) {
    Write-Error "[ERROR] ModelFusion Master CLI (cli.exe) not found. Build via 'cargo build --release --bin cli' or install HugOS IDE."
    exit 1
}

# 2. Discover Database Path
$dbCandidates = @(
    (Join-Path $repoRoot "IDE\db\hf_models.db"),
    "$env:LOCALAPPDATA\HugOS IDE\db\hf_models.db",
    (Join-Path $repoRoot "db\hf_models.db")
)
$dbPath = $dbCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

# 3. Construct arguments and invoke
$mcpArgs = @("--mcp")
if ($dbPath) {
    $mcpArgs += @("--db-path", $dbPath)
}
if ($args) {
    $mcpArgs += $args
}

& $cliBin $mcpArgs
