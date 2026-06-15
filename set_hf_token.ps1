# HuggingFace API Token Setup Script
Write-Host "🔧 HuggingFace API Token Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "This script will help you set your HuggingFace API token." -ForegroundColor Yellow
Write-Host "Get your token from: https://huggingface.co/settings/tokens" -ForegroundColor Yellow
Write-Host ""

$HF_TOKEN = Read-Host "Enter your HuggingFace API token"

if ([string]::IsNullOrWhiteSpace($HF_TOKEN)) {
    Write-Host "❌ No token provided. Setup cancelled." -ForegroundColor Red
    Read-Host "Press Enter to continue"
    exit 1
}

# Set environment variables for current session
$env:HUGGINGFACE_API_KEY = $HF_TOKEN
$env:HF_TOKEN = $HF_TOKEN

Write-Host ""
Write-Host "✅ Token set successfully for current session!" -ForegroundColor Green
Write-Host "💡 You can now run your ensemble commands." -ForegroundColor Green
Write-Host ""

Write-Host "To make this permanent, run these commands in PowerShell as Administrator:" -ForegroundColor Yellow
Write-Host "[Environment]::SetEnvironmentVariable('HUGGINGFACE_API_KEY', '$HF_TOKEN', 'User')" -ForegroundColor Gray
Write-Host "[Environment]::SetEnvironmentVariable('HF_TOKEN', '$HF_TOKEN', 'User')" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to continue"
