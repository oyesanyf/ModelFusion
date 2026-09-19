# HugOS IDE Installer Downloader
# Downloads the latest digitally signed HugOS.msi from GitHub Releases.

$downloadUrl = "https://github.com/oyesanyf/ModelFusion/releases/download/v1.0.0-beta/HugOS.msi"
$outputMsi   = Join-Path $PSScriptRoot "HugOS.msi"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Downloading latest HugOS IDE Installer (Build 93+)..." -ForegroundColor Cyan
Write-Host "URL: $downloadUrl" -ForegroundColor Gray
Write-Host "Target: $outputMsi" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($downloadUrl, $outputMsi)
    Write-Host "[OK] Successfully downloaded latest HugOS.msi ($([math]::Round((Get-Item $outputMsi).Length / 1MB, 2)) MB)" -ForegroundColor Green
    Write-Host "[INFO] To install or upgrade HugOS IDE, run:" -ForegroundColor Yellow
    Write-Host "  msiexec /i `"$outputMsi`"" -ForegroundColor White
} catch {
    Write-Host "[ERROR] Failed to download HugOS.msi: $_" -ForegroundColor Red
    Exit 1
}
