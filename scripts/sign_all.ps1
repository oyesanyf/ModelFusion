# scripts/sign_all.ps1
param(
    [string]$PfxPath = "D:\harfile\ModelFusion\IDE\hugos-signing-cert.pfx",
    [string]$Password = "HugOSPassword123!"
)

if (-not (Test-Path $PfxPath)) {
    Write-Host "[ERROR] Certificate not found at: $PfxPath" -ForegroundColor Red
    Exit 1
}

$pwdSecure = ConvertTo-SecureString $Password -AsPlainText -Force
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 -ArgumentList $PfxPath, $pwdSecure
Write-Host "[OK] Loaded Certificate: $($cert.Subject) (Thumbprint: $($cert.Thumbprint))" -ForegroundColor Green

# Locate signtool if available
$signtoolPath = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
if (-not (Test-Path $signtoolPath)) {
    $candidates = @('C:\Program Files (x86)\Windows Kits', 'C:\Program Files\Windows Kits') | Where-Object { Test-Path $_ }
    if ($candidates) {
        $found = Get-ChildItem -Path $candidates -Filter "signtool.exe" -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -like "*x64*" } | Select-Object -First 1
        if ($found) { $signtoolPath = $found.FullName }
    }
}

$useSigntool = (Test-Path $signtoolPath)
if ($useSigntool) {
    Write-Host "[OK] Using signtool at: $signtoolPath" -ForegroundColor Green
} else {
    Write-Host "[INFO] signtool not found, using Set-AuthenticodeSignature" -ForegroundColor Yellow
}

$targets = @(
    "D:\harfile\ModelFusion\target\release\cli.exe",
    "D:\harfile\ModelFusion\target\release\clibrowser.exe",
    "D:\harfile\ModelFusion\target\release\climcp.exe",
    "D:\harfile\ModelFusion\browser\bin\clibrowser.exe",
    "D:\harfile\ModelFusion\browser\bin\cli.exe",
    "D:\harfile\ModelFusion\IDE\bin\cliide.exe",
    "D:\harfile\ModelFusion\IDE\bin\cli.exe",
    "D:\harfile\ModelFusion\mcp\bin\climcp.exe",
    "D:\harfile\ModelFusion\mcp\bin\cli.exe"
)

foreach ($target in $targets) {
    if (Test-Path $target) {
        Write-Host "Signing: $target ..." -NoNewline
        $signed = $false
        for ($i = 0; $i -lt 2; $i++) {
            if ($useSigntool) {
                & $signtoolPath sign /f $PfxPath /p $Password /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $target 2>$null
                if ($LASTEXITCODE -eq 0) { $signed = $true; break }
                & $signtoolPath sign /f $PfxPath /p $Password /fd SHA256 $target 2>$null
                if ($LASTEXITCODE -eq 0) { $signed = $true; break }
            } else {
                try {
                    $res = Set-AuthenticodeSignature -FilePath $target -Certificate $cert -TimestampServer "http://timestamp.digicert.com" -HashAlgorithm SHA256 -ErrorAction SilentlyContinue
                    if ($res -and $res.SignerCertificate) { $signed = $true; break }
                } catch {}
                try {
                    $res = Set-AuthenticodeSignature -FilePath $target -Certificate $cert -HashAlgorithm SHA256 -ErrorAction SilentlyContinue
                    if ($res -and $res.SignerCertificate) { $signed = $true; break }
                } catch {}
            }
            Start-Sleep -Seconds 1
        }
        if ($signed) {
            Write-Host " [SIGNED]" -ForegroundColor Green
        } else {
            Write-Host " [FAILED TO SIGN]" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n[DONE] Digital signature execution complete!" -ForegroundColor Green

Write-Host "`n[INFO] Submitting all signed binaries to Microsoft Security Intelligence (WDSI)..." -ForegroundColor Yellow
$wdsiScript = Join-Path $PSScriptRoot "submit_to_wdsi.py"
if (Test-Path $wdsiScript) {
    python $wdsiScript --all --no-launch
}
