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

# 0. Terminate any background clibrowser or chrome processes to prevent file locks
Stop-Process -Name clibrowser, chrome -Force -ErrorAction SilentlyContinue

# 1. Verify binary staging
$cliBrowserBinPath = Join-Path $browserDir "bin\clibrowser.exe"
$cliBinPath = Join-Path $browserDir "bin\cli.exe"
$srcCli = Join-Path $rootDir "target\release\cli.exe"
if (-not (Test-Path $srcCli)) {
    $srcCli = Join-Path $rootDir "target\release\clibrowser.exe"
}
if (-not (Test-Path $srcCli)) {
    $srcCli = Join-Path $rootDir "IDE\bin\cli.exe"
}
if (Test-Path $srcCli) {
    New-Item -ItemType Directory -Force -Path (Split-Path $cliBrowserBinPath -Parent) | Out-Null
    Copy-Item -Path $srcCli -Destination $cliBrowserBinPath -Force
    Copy-Item -Path $srcCli -Destination $cliBinPath -Force
    Write-Host "[OK] Staged latest clibrowser.exe and cli.exe from $srcCli into browser\bin" -ForegroundColor Green
} else {
    Write-Host "[ERROR] clibrowser.exe / cli.exe not found at $srcCli. Build release binary first." -ForegroundColor Red
    Exit 1
}

# 1.1 Stage hf_models.db into browser\db and browser\bin\db
$dbCandidates = @(
    (Join-Path $rootDir "IDE\db\hf_models.db"),
    "$env:LOCALAPPDATA\HugOS IDE\db\hf_models.db",
    "$env:LOCALAPPDATA\ModelFusion\db\hf_models.db",
    (Join-Path $rootDir "db\hf_models.db")
)
$dbSrc = $dbCandidates | Where-Object { (Test-Path $_) -and (Get-Item $_).Length -gt 50000 } | Select-Object -First 1
if ($dbSrc) {
    $browserDb = Join-Path $browserDir "db\hf_models.db"
    $browserBinDb = Join-Path $browserDir "bin\db\hf_models.db"
    New-Item -ItemType Directory -Force -Path (Split-Path $browserDb -Parent) | Out-Null
    New-Item -ItemType Directory -Force -Path (Split-Path $browserBinDb -Parent) | Out-Null
    try {
        if (-not (Test-Path $browserDb) -or (Get-Item $browserDb).Length -ne (Get-Item $dbSrc).Length) {
            Copy-Item -Path $dbSrc -Destination $browserDb -Force
        }
    } catch {
        Write-Host "[WARN] $browserDb in use, proceeding with existing file." -ForegroundColor Yellow
    }
    try {
        if (-not (Test-Path $browserBinDb) -or (Get-Item $browserBinDb).Length -ne (Get-Item $dbSrc).Length) {
            Copy-Item -Path $dbSrc -Destination $browserBinDb -Force
        }
    } catch {
        Write-Host "[WARN] $browserBinDb in use, proceeding with existing file." -ForegroundColor Yellow
    }
    Write-Host "[OK] Staged hf_models.db ($( (Get-Item $browserDb).Length ) bytes) into browser\db and browser\bin\db" -ForegroundColor Green
} else {
    Write-Host "[WARNING] No populated hf_models.db found for browser packaging." -ForegroundColor Yellow
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
$signCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 -ArgumentList $pfxPath, $pwdSecure

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
    $existingSig = Get-AuthenticodeSignature $f.FullName -ErrorAction SilentlyContinue
    if ($existingSig -and $existingSig.SignerCertificate -ne $null) {
        Write-Host "  [ALREADY SIGNED] $($f.Name)" -ForegroundColor Green
        continue
    }
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

# Keep msiserver active during WiX build
$comInstaller = $null
try {
    Start-Service -Name msiserver -ErrorAction SilentlyContinue
    $comInstaller = New-Object -ComObject WindowsInstaller.Installer
} catch {}

$wixOutLog = Join-Path $browserDir "wix_browser_stdout.log"
$wixErrLog = Join-Path $browserDir "wix_browser_stderr.log"
if (Test-Path $wixOutLog) { Remove-Item $wixOutLog -Force -ErrorAction SilentlyContinue }
if (Test-Path $wixErrLog) { Remove-Item $wixErrLog -Force -ErrorAction SilentlyContinue }

$wixProc = Start-Process -FilePath $wixExe -ArgumentList "build", "-b", "`"$browserDir`"", "-arch", "x64", "`"$wxsPath`"", "-out", "`"$msiPath`"" -NoNewWindow -PassThru -RedirectStandardOutput $wixOutLog -RedirectStandardError $wixErrLog
while (-not $wixProc.HasExited) {
    try {
        $msiSvc = Get-Service msiserver -ErrorAction SilentlyContinue
        if ($msiSvc -and $msiSvc.Status -ne 'Running') {
            Start-Service -Name msiserver -ErrorAction SilentlyContinue
        }
    } catch {}
    Start-Sleep -Seconds 1
}
$wixProc.WaitForExit()
$wixExit = if ($wixProc.ExitCode -ne $null) { [int]$wixProc.ExitCode } else { 0 }

# Release COM keepalive
$comInstaller = $null
[System.GC]::Collect()

if ((Test-Path $msiPath) -and (Get-Item $msiPath).Length -gt 10MB) {
    Write-Host "[OK] MSI built successfully at $msiPath ($([math]::Round((Get-Item $msiPath).Length / 1MB, 2)) MB)" -ForegroundColor Green
} elseif ($wixExit -ne 0 -or -not (Test-Path $msiPath)) {
    Write-Host "[ERROR] WiX build failed (Exit code: $wixExit)." -ForegroundColor Red
    if (Test-Path $wixErrLog) { Get-Content $wixErrLog | Write-Host -ForegroundColor Red }
    if (Test-Path $wixOutLog) { Get-Content $wixOutLog -Tail 50 | Write-Host -ForegroundColor Yellow }
    Exit 1
}

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
