#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Complete PE Header Extractor - Extracts ALL PE Headers from Binary Files
    
.DESCRIPTION
    This script extracts ALL PE header fields comprehensively from binary files including:
    - DOS Header (all fields)
    - File Header (all fields) 
    - Optional Header (all fields)
    - Data Directories (all 16 directories)
    - Sections (all section details with entropy)
    - Imports (all imported functions)
    - Exports (all exported functions)
    - Resources (all resource details)
    - File hashes (MD5, SHA1, SHA256, SHA512)
    - Characteristic flags
    - Summary statistics

.PARAMETER BinaryFile
    Path to the binary file to analyze

.PARAMETER OutputJson
    Optional output JSON file path. If not specified, will use <filename>_complete_pe_analysis.json

.EXAMPLE
    .\extract_all_pe_headers.ps1 malware.exe
    
.EXAMPLE
    .\extract_all_pe_headers.ps1 suspicious.dll analysis.json
    
.NOTES
    Requires Python and pefile module to be installed
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$BinaryFile,
    
    [Parameter(Mandatory=$false, Position=1)]
    [string]$OutputJson
)

# Function to write colored output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Function to check if Python is available
function Test-PythonAvailable {
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    }
    catch {
        return $false
    }
    return $false
}

# Function to check if pefile module is available
function Test-PefileAvailable {
    try {
        $result = python -c "import pefile; print('pefile available')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    }
    catch {
        return $false
    }
    return $false
}

# Main script
Write-ColorOutput "========================================" "Cyan"
Write-ColorOutput "COMPLETE PE HEADER EXTRACTOR" "Cyan"
Write-ColorOutput "========================================" "Cyan"
Write-Host ""

# Check if binary file exists
if (-not (Test-Path $BinaryFile)) {
    Write-ColorOutput "ERROR: File '$BinaryFile' not found!" "Red"
    exit 1
}

# Check if Python is available
if (-not (Test-PythonAvailable)) {
    Write-ColorOutput "ERROR: Python is not available or not in PATH!" "Red"
    Write-ColorOutput "Please install Python and ensure it's in your PATH." "Yellow"
    exit 1
}

# Check if pefile module is available
if (-not (Test-PefileAvailable)) {
    Write-ColorOutput "ERROR: pefile module is not available!" "Red"
    Write-ColorOutput "Please install pefile module: pip install pefile" "Yellow"
    exit 1
}

# Set output JSON file if not specified
if (-not $OutputJson) {
    $fileName = [System.IO.Path]::GetFileNameWithoutExtension($BinaryFile)
    $OutputJson = "${fileName}_complete_pe_analysis.json"
}

Write-ColorOutput "Extracting ALL PE headers from: $BinaryFile" "Green"
Write-ColorOutput "Output will be saved to: $OutputJson" "Green"
Write-Host ""

# Run the Python script
try {
    $result = python complete_pe_header_extractor.py $BinaryFile $OutputJson 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-ColorOutput "========================================" "Green"
        Write-ColorOutput "EXTRACTION COMPLETED SUCCESSFULLY!" "Green"
        Write-ColorOutput "========================================" "Green"
        Write-ColorOutput "All PE headers have been extracted and saved to: $OutputJson" "Green"
        Write-Host ""
        Write-ColorOutput "The analysis includes:" "Green"
        Write-ColorOutput "  ✓ Complete DOS Header" "White"
        Write-ColorOutput "  ✓ Complete File Header" "White"
        Write-ColorOutput "  ✓ Complete Optional Header" "White"
        Write-ColorOutput "  ✓ All Data Directories" "White"
        Write-ColorOutput "  ✓ All Sections with Entropy" "White"
        Write-ColorOutput "  ✓ All Imports and Exports" "White"
        Write-ColorOutput "  ✓ All Resources" "White"
        Write-ColorOutput "  ✓ File Hashes (MD5, SHA1, SHA256, SHA512)" "White"
        Write-ColorOutput "  ✓ Characteristic Flags" "White"
        Write-ColorOutput "  ✓ Summary Statistics" "White"
        Write-Host ""
        
        # Show file size of output
        if (Test-Path $OutputJson) {
            $fileSize = (Get-Item $OutputJson).Length
            Write-ColorOutput "Output file size: $fileSize bytes" "Cyan"
        }
    }
    else {
        Write-Host ""
        Write-ColorOutput "========================================" "Red"
        Write-ColorOutput "EXTRACTION FAILED!" "Red"
        Write-ColorOutput "========================================" "Red"
        Write-ColorOutput "Check the error messages above." "Yellow"
        Write-Host ""
        Write-ColorOutput "Error output:" "Red"
        Write-Host $result
    }
}
catch {
    Write-ColorOutput "ERROR: Failed to run Python script: $($_.Exception.Message)" "Red"
    exit 1
}

Write-Host ""
Write-ColorOutput "Press any key to continue..." "Gray"
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 