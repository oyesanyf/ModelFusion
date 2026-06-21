# Aether IDE Build & Run Helper

$vsCodeDir = Join-Path $PSScriptRoot "vscode"
if (-not (Test-Path $vsCodeDir)) {
    Write-Host "❌ vscode directory not found. Please clone it first." -ForegroundColor Red
    Exit 1
}

# Change directory
Set-Location $vsCodeDir

# Check node_modules
$nodeModules = Join-Path $vsCodeDir "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "📦 Installing dependencies via Yarn (this may take a few minutes)..." -ForegroundColor Yellow
    & yarn install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies." -ForegroundColor Red
        Exit 1
    }
    Write-Host "✅ Dependencies installed." -ForegroundColor Green
}

# Run build watch in a separate window, then launch Code
Write-Host "🌀 Starting Aether IDE build watch loop in a separate window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$vsCodeDir'; yarn watch"

Write-Host "🚀 Launching Aether IDE..." -ForegroundColor Green
Start-Sleep -Seconds 5
& .\scripts\code.bat
