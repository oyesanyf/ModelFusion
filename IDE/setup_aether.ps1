# Aether IDE Setup Script

Write-Host "🌀 Welcome to Aether IDE setup!" -ForegroundColor Cyan

# 1. Check prerequisites
Write-Host "🔍 Checking prerequisites..." -ForegroundColor Yellow
$prereqs = @{
    "git" = "git --version"
    "node" = "node --version"
    "yarn" = "yarn --version"
}

foreach ($name in $prereqs.Keys) {
    try {
        $cmd = $prereqs[$name]
        Invoke-Expression $cmd | Out-Null
        Write-Host "  ✅ $name is installed." -ForegroundColor Green
    } catch {
        Write-Host "  ❌ $name is NOT installed. Please install it before proceeding." -ForegroundColor Red
        Exit 1
    }
}

# 2. Clone VS Code
$vsCodeDir = Join-Path $PSScriptRoot "vscode"
if (-not (Test-Path $vsCodeDir)) {
    Write-Host "📥 Cloning microsoft/vscode repository..." -ForegroundColor Yellow
    git clone --depth 1 https://github.com/microsoft/vscode.git $vsCodeDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to clone VS Code repository." -ForegroundColor Red
        Exit 1
    }
    Write-Host "✅ Clone complete." -ForegroundColor Green
} else {
    Write-Host "✅ VS Code repository already cloned." -ForegroundColor Green
}

# 3. Apply custom branding
Write-Host "🎨 Applying custom Aether branding..." -ForegroundColor Yellow
$productJsonPath = Join-Path $vsCodeDir "product.json"
if (Test-Path $productJsonPath) {
    # Read product.json as raw string, replace/inject settings, or parse as JSON
    $productText = Get-Content $productJsonPath -Raw
    $product = ConvertFrom-Json $productText
    
    # Update names
    $product.nameShort = "Aether"
    $product.nameLong = "Aether IDE"
    $product.applicationName = "aether"
    $product.win32AppId = "{{AETHER-IDE-APPID}}"
    $product.win32AppUserModelId = "Aether.Aether"
    $product.win32MutexName = "aether"
    
    # Configure Open VSX Marketplace
    $gallery = @{
        "serviceUrl" = "https://open-vsx.org/api/xquery"
        "itemUrl" = "https://open-vsx.org/item"
    }
    $product | Add-Member -MemberType NoteProperty -Name "extensionsGallery" -Value $gallery -Force
    
    $product | ConvertTo-Json -Depth 100 | Out-File $productJsonPath -Encoding utf8
    Write-Host "  ✅ product.json branding and extensions gallery updated." -ForegroundColor Green
}

# Update package.json
$packageJsonPath = Join-Path $vsCodeDir "package.json"
if (Test-Path $packageJsonPath) {
    $packageText = Get-Content $packageJsonPath -Raw
    $package = ConvertFrom-Json $packageText
    $package.name = "aether"
    $package.displayName = "Aether"
    $package.description = "Aether - Custom AI-Powered Code-OSS IDE"
    $package.author = @{ "name" = "Aether Team" }
    
    $package | ConvertTo-Json -Depth 100 | Out-File $packageJsonPath -Encoding utf8
    Write-Host "  ✅ package.json updated." -ForegroundColor Green
}

Write-Host "🚀 Aether IDE configuration initialized successfully!" -ForegroundColor Green
Write-Host "To compile and launch Aether:" -ForegroundColor Cyan
Write-Host "  1. Open a terminal in: $vsCodeDir" -ForegroundColor White
Write-Host "  2. Run 'yarn' to install dependencies" -ForegroundColor White
Write-Host "  3. Run 'yarn watch' to start compiler watch loop" -ForegroundColor White
Write-Host "  4. In a separate terminal, run '.\scripts\code.bat' to launch Aether!" -ForegroundColor White
