@echo off
REM Complete PE Header Extractor Batch Script
REM Extracts ALL PE headers from binary files

echo ========================================
echo COMPLETE PE HEADER EXTRACTOR
echo ========================================
echo.

if "%1"=="" (
    echo Usage: extract_all_pe_headers.bat ^<binary_file^> [output_json]
    echo.
    echo Examples:
    echo   extract_all_pe_headers.bat malware.exe
    echo   extract_all_pe_headers.bat suspicious.dll analysis.json
    echo.
    echo This will extract ALL PE headers including:
    echo   - DOS Header (all fields)
    echo   - File Header (all fields)
    echo   - Optional Header (all fields)
    echo   - Data Directories (all 16 directories)
    echo   - Sections (all section details)
    echo   - Imports (all imported functions)
    echo   - Exports (all exported functions)
    echo   - Resources (all resource details)
    echo   - File hashes (MD5, SHA1, SHA256, SHA512)
    echo   - Entropy calculations
    echo   - Characteristic flags
    echo.
    pause
    exit /b 1
)

set BINARY_FILE=%1
set OUTPUT_JSON=%2

if not exist "%BINARY_FILE%" (
    echo ERROR: File "%BINARY_FILE%" not found!
    pause
    exit /b 1
)

if "%OUTPUT_JSON%"=="" (
    for %%i in ("%BINARY_FILE%") do set OUTPUT_JSON=%%~ni_complete_pe_analysis.json
)

echo Extracting ALL PE headers from: %BINARY_FILE%
echo Output will be saved to: %OUTPUT_JSON%
echo.

python complete_pe_header_extractor.py "%BINARY_FILE%" "%OUTPUT_JSON%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo EXTRACTION COMPLETED SUCCESSFULLY!
    echo ========================================
    echo All PE headers have been extracted and saved to: %OUTPUT_JSON%
    echo.
    echo The analysis includes:
    echo   ✓ Complete DOS Header
    echo   ✓ Complete File Header  
    echo   ✓ Complete Optional Header
    echo   ✓ All Data Directories
    echo   ✓ All Sections with Entropy
    echo   ✓ All Imports and Exports
    echo   ✓ All Resources
    echo   ✓ File Hashes (MD5, SHA1, SHA256, SHA512)
    echo   ✓ Characteristic Flags
    echo   ✓ Summary Statistics
    echo.
) else (
    echo.
    echo ========================================
    echo EXTRACTION FAILED!
    echo ========================================
    echo Check the error messages above.
    echo.
)

pause 