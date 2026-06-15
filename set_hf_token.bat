@echo off
echo 🔧 HuggingFace API Token Setup
echo ================================
echo.
echo This script will help you set your HuggingFace API token.
echo Get your token from: https://huggingface.co/settings/tokens
echo.
set /p HF_TOKEN="Enter your HuggingFace API token: "
if "%HF_TOKEN%"=="" (
    echo ❌ No token provided. Setup cancelled.
    pause
    exit /b 1
)
echo.
echo ✅ Token set successfully!
echo 💡 You can now run your ensemble commands.
echo.
echo To make this permanent, add this to your system environment variables:
echo HUGGINGFACE_API_KEY=%HF_TOKEN%
echo HF_TOKEN=%HF_TOKEN%
echo.
pause
