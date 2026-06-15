
$ErrorActionPreference = "SilentlyContinue"
Write-Host "Monitoring database recovery..."

$dumpProcessName = "sqlite3"
$completed = $false

while (-not $completed) {
    $proc = Get-Process -Name $dumpProcessName -ErrorAction SilentlyContinue
    if ($proc) {
        $sqlFile = "..\db\recovered.sql"
        if (Test-Path $sqlFile) {
            $size = (Get-Item $sqlFile).Length / 1MB
            Write-Host -NoNewline ("`rDump in progress... Recovered SQL Size: {0:N2} MB" -f $size)
        }
        Start-Sleep -Seconds 5
    }
    else {
        $completed = $true
        Write-Host "`nDump process finished."
    }
}

Write-Host "Starting restoration phase..."
& ./restore_db_from_sql.ps1
