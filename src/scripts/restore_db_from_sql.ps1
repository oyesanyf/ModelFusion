
$ErrorActionPreference = "Stop"
Write-Host "Starting database restoration..."
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Script is in src/scripts. Go up two levels to project root, then into db.
$dbDir = Join-Path $scriptDir "..\..\db"
$dbPath = Join-Path $dbDir "hf_models.db"
$sqlPath = Join-Path $dbDir "recovered.sql"

if (-not (Test-Path $sqlPath)) {
    Write-Error "SQL recovery file not found at $sqlPath"
}

if (Test-Path $dbPath) {
    Write-Host "Removing existing target DB..."
    Remove-Item $dbPath
}

Write-Host "Importing SQL from $sqlPath to $dbPath..."
Write-Host "This may take several minutes..."

# Use cmd /c for reliable redirection
$cmd = "sqlite3 ""$dbPath"" < ""$sqlPath"""
cmd /c $cmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "Restoration complete!"
    if (Test-Path $dbPath) {
        $size = (Get-Item $dbPath).Length / 1MB
        Write-Host ("New DB Size: {0:N2} MB" -f $size)
        
        # Verify
        Write-Host "Verifying integrity..."
        $verify = cmd /c "sqlite3 ""$dbPath"" ""PRAGMA integrity_check;"""
        Write-Host "Integrity Check: $verify"
    }
    else {
        Write-Error "Database file was not created!"
    }
}
else {
    Write-Error "Error during restoration. Exit code: $LASTEXITCODE"
}
