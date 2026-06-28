# HugOS IDE Signed MSI Packaging Script
# This script compiles, copies cli.exe, signs all binaries, generates a WiX manifest, and builds/signs the final MSI.

$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$vsCodePackDir = Join-Path (Split-Path $PSScriptRoot -Parent) "IDE\VSCode-win32-x64"
$pfxPath = Join-Path $PSScriptRoot "hugos-signing-cert.pfx"
$password = "HugOSPassword123!"

Write-Host "--------------------------------------------------------" -ForegroundColor Green
Write-Host "[START] Starting HugOS IDE Signed MSI Packaging Process" -ForegroundColor Green
Write-Host "--------------------------------------------------------" -ForegroundColor Green

# 1. Verify VSCode-win32-x64 directory exists
if (-not (Test-Path $vsCodePackDir)) {
    Write-Host "[ERROR] Packaged directory not found at: $vsCodePackDir" -ForegroundColor Red
    Write-Host "Please make sure the gulp package task (vscode-win32-x64) has finished." -ForegroundColor Yellow
    Exit 1
}
Write-Host "[OK] Resolved packaged VS Code directory at $vsCodePackDir" -ForegroundColor Green

# 2. Locate signtool.exe
$signtoolPath = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
if (-not (Test-Path $signtoolPath)) {
    Write-Host "[INFO] Signtool not found at default path, searching Windows Kits..." -ForegroundColor Yellow
    $signtoolPath = Get-ChildItem -Path 'C:\Program Files (x86)\Windows Kits' -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue | 
                    Where-Object { $_.FullName -like "*x64*" } | 
                    Select-Object -ExpandProperty FullName -First 1
}

if (-not $signtoolPath) {
    Write-Host "[ERROR] signtool.exe could not be found on this system. Please install the Windows SDK." -ForegroundColor Red
    Exit 1
}
Write-Host "[OK] Using signtool at: $signtoolPath" -ForegroundColor Green

# 3. Code Signing Certificate Setup
if (-not (Test-Path $pfxPath)) {
    Write-Host "[INFO] Creating a self-signed code signing certificate..." -ForegroundColor Yellow
    
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=HugOS IDE" -FriendlyName "HugOS Code Signing" -CertStoreLocation "Cert:\CurrentUser\My"
    $pwdSecure = ConvertTo-SecureString $password -AsPlainText -Force
    Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pwdSecure
    
    Write-Host "[OK] Certificate created at: $pfxPath" -ForegroundColor Green
} else {
    Write-Host "[OK] Found existing signing certificate at $pfxPath" -ForegroundColor Green
}

# 4. Copy ModelFusion CLI (cli.exe) into the packaged folder
$cliSrcPath = Join-Path (Split-Path $PSScriptRoot -Parent) "target\release\cli.exe"
if (-not (Test-Path $cliSrcPath)) {
    Write-Host "[ERROR] ModelFusion cli.exe not found at $cliSrcPath. Run 'cargo build --release' first." -ForegroundColor Red
    Exit 1
}

$cliDestDir = Join-Path $vsCodePackDir "bin"
if (-not (Test-Path $cliDestDir)) {
    New-Item -ItemType Directory -Force -Path $cliDestDir | Out-Null
}

$cliDestPath = Join-Path $cliDestDir "cli.exe"
Copy-Item -Path $cliSrcPath -Destination $cliDestPath -Force
Write-Host "[OK] Copied ModelFusion CLI to: $cliDestPath" -ForegroundColor Green

# 5. Sign the binaries
Write-Host "[INFO] Signing executables, DLLs, and native modules inside packaged folder..." -ForegroundColor Yellow
$filesToSign = Get-ChildItem -Path $vsCodePackDir -Include *.exe, *.dll, *.node -Recurse | Select-Object -ExpandProperty FullName

$count = 0
foreach ($file in $filesToSign) {
    # Skip files that are already signed or fail to sign (like some readonly or system files)
    # We will attempt to sign with a retry in case of transient timestamp issues
    Write-Host "Signing: $file"
    $signed = $false
    for ($i = 0; $i -lt 2; $i++) {
        # Try signing with timestamp
        & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $file 2>$null
        if ($LASTEXITCODE -eq 0) {
            $signed = $true
            break
        }
        # Try signing without timestamp as fallback
        & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 $file 2>$null
        if ($LASTEXITCODE -eq 0) {
            $signed = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if ($signed) { $count++ }
}
Write-Host "[OK] Signed $count files inside the packaging directory." -ForegroundColor Green

# 6. Generate the WiX source manifest (.wxs)
Write-Host "[INFO] Generating WiX source manifest (.wxs)..." -ForegroundColor Yellow
$wxsPath = Join-Path $PSScriptRoot "HugOS.wxs"
node (Join-Path $PSScriptRoot "generate_wix.js") $vsCodePackDir $wxsPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to run generate_wix.js." -ForegroundColor Red
    Exit 1
}
Write-Host "[OK] WiX source generated at $wxsPath" -ForegroundColor Green

# 7. Compile the MSI using WiX Toolset v7
Write-Host "[INFO] Compiling MSI using WiX Toolset v7..." -ForegroundColor Yellow
$msiPath = Join-Path $PSScriptRoot "HugOS.msi"
if (Test-Path $msiPath) {
    Remove-Item -Path $msiPath -Force
}

# Run wix build
& wix build -arch x64 $wxsPath -out $msiPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] WiX build failed." -ForegroundColor Red
    Exit 1
}
Write-Host "[OK] MSI built successfully at $msiPath" -ForegroundColor Green

# 8. Sign the final MSI file
Write-Host "[INFO] Signing final MSI package..." -ForegroundColor Yellow
$signedMsi = $false
for ($i = 0; $i -lt 3; $i++) {
    & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $msiPath
    if ($LASTEXITCODE -eq 0) {
        $signedMsi = $true
        break
    }
    & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 $msiPath
    if ($LASTEXITCODE -eq 0) {
        $signedMsi = $true
        break
    }
    Start-Sleep -Seconds 2
}

if ($signedMsi) {
    Write-Host "[OK] Signed final MSI installer successfully!" -ForegroundColor Green
    & $signtoolPath verify /pa $msiPath
    Write-Host "[SUCCESS] Process complete. MSI installer generated at: $msiPath" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to sign final MSI installer." -ForegroundColor Red
    Exit 1
}
