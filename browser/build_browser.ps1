# HugOS Browser Signed MSI Packaging Script
# Compiles manifest, verifies binaries, signs executables and MSI package using WiX Toolset.

$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$rootDir = Split-Path $PSScriptRoot -Parent
$browserDir = $PSScriptRoot
$pfxPath = Join-Path $rootDir "IDE\hugos-signing-cert.pfx"
$password = "HugOSPassword123!"

# Ensure common tools are available in PATH
$toolDirs = @(
    "D:\tools\nodejs",
    "D:\tools\wix\PFiles64\WiX Toolset v5.0\bin",
    "C:\Users\oyesanyf\wix_tools\PFiles64\WiX Toolset v5.0\bin",
    "C:\Program Files\dotnet"
)
foreach ($td in $toolDirs) {
    if ((Test-Path $td) -and ($env:PATH -notlike "*$td*")) {
        $env:PATH = "$td;" + $env:PATH
    }
}

Write-Host "--------------------------------------------------------" -ForegroundColor Green
Write-Host "[START] Starting HugOS Browser Signed MSI Packaging Process" -ForegroundColor Green
Write-Host "--------------------------------------------------------" -ForegroundColor Green

# 1. Verify binary staging
$cliBinPath = Join-Path $browserDir "bin\cli.exe"
if (-not (Test-Path $cliBinPath)) {
    $srcCli = Join-Path $rootDir "target\release\cli.exe"
    if (-not (Test-Path $srcCli)) {
        $srcCli = Join-Path $rootDir "IDE\bin\cli.exe"
    }
    if (Test-Path $srcCli) {
        New-Item -ItemType Directory -Force -Path (Split-Path $cliBinPath -Parent) | Out-Null
        Copy-Item -Path $srcCli -Destination $cliBinPath -Force
        Write-Host "[OK] Staged cli.exe from $srcCli" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] cli.exe not found. Build release binary first." -ForegroundColor Red
        Exit 1
    }
}

# 2. Locate signtool or PowerShell Authenticode
$signtoolPath = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
if (-not (Test-Path $signtoolPath)) {
    $candidatePaths = @('C:\Program Files (x86)\Windows Kits', 'C:\Program Files\Windows Kits') | Where-Object { Test-Path $_ }
    if ($candidatePaths) {
        $signtoolPath = Get-ChildItem -Path $candidatePaths -Filter signtool.exe -Recurse -Depth 4 -ErrorAction SilentlyContinue | 
                        Where-Object { $_.FullName -like "*x64*" } | 
                        Select-Object -ExpandProperty FullName -First 1
    } else {
        $signtoolPath = $null
    }
}

$pwdSecure = ConvertTo-SecureString $password -AsPlainText -Force
$signCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($pfxPath, $pwdSecure)

function Sign-FileWithCert {
    param([string]$FilePath)
    if ($signtoolPath) {
        for ($i = 0; $i -lt 2; $i++) {
            & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $FilePath 2>$null
            if ($LASTEXITCODE -eq 0) { return $true }
            & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 $FilePath 2>$null
            if ($LASTEXITCODE -eq 0) { return $true }
            Start-Sleep -Seconds 1
        }
        return $false
    } else {
        for ($i = 0; $i -lt 2; $i++) {
            try {
                $res = Set-AuthenticodeSignature -FilePath $FilePath -Certificate $signCert -TimestampServer "http://timestamp.digicert.com" -HashAlgorithm SHA256 -ErrorAction SilentlyContinue
                if ($res -and $res.SignerCertificate) { return $true }
            } catch {}
            try {
                $res = Set-AuthenticodeSignature -FilePath $FilePath -Certificate $signCert -HashAlgorithm SHA256 -ErrorAction SilentlyContinue
                if ($res -and $res.SignerCertificate) { return $true }
            } catch {}
            Start-Sleep -Seconds 1
        }
        return $false
    }
}

# 3. Sign Binaries
Write-Host "[INFO] Signing internal binaries..." -ForegroundColor Yellow
$filesToSign = Get-ChildItem -Path $browserDir -Include *.exe, *.dll -Recurse | Where-Object { $_.FullName -notlike "*node_modules*" }
foreach ($f in $filesToSign) {
    $ok = Sign-FileWithCert -FilePath $f.FullName
    if ($ok) {
        Write-Host "  [SIGNED] $($f.Name)" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Failed to sign $($f.Name)" -ForegroundColor Yellow
    }
}

# 4. Generate WiX Source Manifest (.wxs)
Write-Host "[INFO] Generating WiX source manifest for HugOS Browser..." -ForegroundColor Yellow
$wxsPath = Join-Path $browserDir "HugOS_Browser.wxs"
$nodeExe = "D:\tools\nodejs\node.exe"
if (-not (Test-Path $nodeExe)) {
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    $nodeExe = if ($nodeCmd) { $nodeCmd.Source } else { "node" }
}

& $nodeExe (Join-Path $browserDir "generate_wix.js") $browserDir $wxsPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to run generate_wix.js" -ForegroundColor Red
    Exit 1
}
Write-Host "[OK] WiX manifest generated at $wxsPath" -ForegroundColor Green

# 5. Compile the MSI using WiX Toolset
Write-Host "[INFO] Compiling HugOS_Browser.msi using WiX Toolset..." -ForegroundColor Yellow
$msiPath = Join-Path $browserDir "HugOS_Browser.msi"
if (Test-Path $msiPath) {
    Remove-Item -Path $msiPath -Force
}

$wixExe = "D:\tools\wix\PFiles64\WiX Toolset v5.0\bin\wix.exe"
if (-not (Test-Path $wixExe)) {
    $wixExe = "C:\Users\oyesanyf\wix_tools\PFiles64\WiX Toolset v5.0\bin\wix.exe"
}
if (-not (Test-Path $wixExe)) {
    $wixCmd = Get-Command wix -ErrorAction SilentlyContinue
    $wixExe = if ($wixCmd) { $wixCmd.Source } else { "wix" }
}

& $wixExe build -b $browserDir -arch x64 -ct 4 $wxsPath -out $msiPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] WiX build failed." -ForegroundColor Red
    Exit 1
}
Write-Host "[OK] MSI built successfully at $msiPath" -ForegroundColor Green

# 6. Sign final MSI
Write-Host "[INFO] Digitally signing HugOS_Browser.msi..." -ForegroundColor Yellow
$msiSigned = Sign-FileWithCert -FilePath $msiPath
if ($msiSigned) {
    Write-Host "[OK] HugOS_Browser.msi signed successfully!" -ForegroundColor Green
} else {
    Write-Host "[WARN] Warning: HugOS_Browser.msi signing returned non-zero" -ForegroundColor Yellow
}

$hash = (Get-FileHash -Path $msiPath -Algorithm SHA256).Hash
$sizeMb = [math]::Round((Get-Item $msiPath).Length / 1MB, 2)
Write-Host "--------------------------------------------------------" -ForegroundColor Green
Write-Host "[DONE] HugOS Browser Packaging Complete!" -ForegroundColor Green
Write-Host "MSI File : $msiPath" -ForegroundColor Cyan
Write-Host "Size     : $sizeMb MB" -ForegroundColor Cyan
Write-Host "SHA-256  : $hash" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------" -ForegroundColor Green
