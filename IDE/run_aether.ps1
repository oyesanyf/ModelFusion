# Aether IDE Build & Run Helper

$vsCodeDir = Join-Path $PSScriptRoot "vscode"
if (-not (Test-Path $vsCodeDir)) {
    Write-Host "[ERROR] vscode directory not found. Please clone it first." -ForegroundColor Red
    Exit 1
}

# Change directory
Set-Location $vsCodeDir

# Check node_modules
$nodeModules = Join-Path $vsCodeDir "node_modules"
# Add node to path in case it is not globally in the path yet (just-installed case)
$env:Path += ";C:\Program Files\nodejs"

if (-not (Test-Path $nodeModules)) {
    Write-Host "[INFO] Installing dependencies via npm (this may take a few minutes)..." -ForegroundColor Yellow
    & npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install dependencies." -ForegroundColor Red
        Exit 1
    }
    Write-Host "[OK] Dependencies installed." -ForegroundColor Green
}

# Run build watch in a separate window, then launch Code
Write-Host "[BUILD] Starting Aether IDE build watch loop in a separate window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$vsCodeDir'; `$env:Path += ';C:\Program Files\nodejs'; npm run watch"

# Wait for the initial compilation to generate out/main.js
$mainJs = Join-Path $vsCodeDir "out\main.js"
if (-not (Test-Path $mainJs)) {
    Write-Host "[INFO] Waiting for the initial compilation to finish and generate out\main.js (this may take 30-60 seconds)..." -ForegroundColor Yellow
    $timeout = 180 # 3 minutes max
    $elapsed = 0
    while (-not (Test-Path $mainJs) -and $elapsed -lt $timeout) {
        Start-Sleep -Seconds 2
        $elapsed += 2
        Write-Host "." -NoNewline
    }
    Write-Host ""
    if (-not (Test-Path $mainJs)) {
        Write-Host "[ERROR] Compilation timed out. Please check the other PowerShell window for errors." -ForegroundColor Red
        Exit 1
    }
    Write-Host "[OK] Compilation finished successfully." -ForegroundColor Green
}

Write-Host "[RUN] Launching Aether IDE..." -ForegroundColor Green
& .\scripts\code.bat
