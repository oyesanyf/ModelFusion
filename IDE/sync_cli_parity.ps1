$rootDir = Split-Path -Parent $PSScriptRoot
$src = Join-Path $rootDir "target\release\cli.exe"
$targets = @(
    (Join-Path $rootDir "IDE\bin\cli.exe"),
    (Join-Path $rootDir "IDE\VSCode-win32-x64\bin\cli.exe"),
    "$env:LOCALAPPDATA\HugOS IDE\bin\cli.exe",
    (Join-Path $rootDir "browser\bin\cli.exe"),
    "$env:LOCALAPPDATA\HugOS Browser\bin\cli.exe"
)

foreach ($t in $targets) {
    $parent = Split-Path -Parent $t
    if (!(Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Copy-Item -Path $src -Destination $t -Force
}

$all = @($src) + $targets
Write-Host "=== CRYPTOGRAPHIC 6-WAY PARITY VERIFICATION (CLI.EXE) ==="
foreach ($f in $all) {
    if (Test-Path $f) {
        $h = (Get-FileHash -Path $f -Algorithm SHA256).Hash
        $s = (Get-Item $f).Length
        Write-Host "$h | $s bytes | $f"
    } else {
        Write-Host "MISSING: $f"
    }
}

# ---------------------------------------------------------------------------
# Database Auto-Sync: hf_models.db across all installation & runtime folders
# ---------------------------------------------------------------------------
$dbCandidates = @(
    (Join-Path $rootDir "IDE\db\hf_models.db"),
    "$env:LOCALAPPDATA\HugOS IDE\db\hf_models.db",
    "$env:LOCALAPPDATA\ModelFusion\db\hf_models.db",
    (Join-Path $rootDir "db\hf_models.db")
)
$populatedDbSrc = $dbCandidates | Where-Object { (Test-Path $_) -and (Get-Item $_).Length -gt 50000 } | Select-Object -First 1

if ($populatedDbSrc) {
    Write-Host "`n=== SYNCHRONIZING HF_MODELS.DB ACROSS INSTALLATION DIRECTORIES ==="
    Write-Host "Populated DB Source: $populatedDbSrc ($( (Get-Item $populatedDbSrc).Length ) bytes)"

    $dbTargets = @(
        (Join-Path $rootDir "IDE\db\hf_models.db"),
        (Join-Path $rootDir "IDE\bin\db\hf_models.db"),
        (Join-Path $rootDir "IDE\VSCode-win32-x64\db\hf_models.db"),
        (Join-Path $rootDir "IDE\VSCode-win32-x64\bin\db\hf_models.db"),
        "$env:LOCALAPPDATA\HugOS IDE\db\hf_models.db",
        "$env:LOCALAPPDATA\HugOS IDE\bin\db\hf_models.db",
        (Join-Path $rootDir "browser\db\hf_models.db"),
        (Join-Path $rootDir "browser\bin\db\hf_models.db"),
        "$env:LOCALAPPDATA\HugOS Browser\db\hf_models.db",
        "$env:LOCALAPPDATA\HugOS Browser\bin\db\hf_models.db",
        "$env:LOCALAPPDATA\ModelFusion\db\hf_models.db"
    )

    if (Test-Path "C:\harfile") {
        $dbTargets += "C:\harfile\db\hf_models.db"
    }

    $populatedLen = (Get-Item $populatedDbSrc).Length
    foreach ($dt in $dbTargets) {
        $parent = Split-Path -Parent $dt
        if (!(Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        if (-not (Test-Path $dt) -or (Get-Item $dt).Length -ne $populatedLen) {
            Copy-Item -Path $populatedDbSrc -Destination $dt -Force
            Write-Host "[COPIED] $dt ($( (Get-Item $dt).Length ) bytes)"
        } else {
            Write-Host "[EXISTS] $dt ($( (Get-Item $dt).Length ) bytes)"
        }
    }

    Write-Host "`n=== CRYPTOGRAPHIC DATABASE PARITY VERIFICATION (HF_MODELS.DB) ==="
    foreach ($f in $dbTargets) {
        if (Test-Path $f) {
            $h = (Get-FileHash -Path $f -Algorithm SHA256).Hash
            $s = (Get-Item $f).Length
            Write-Host "$h | $s bytes | $f"
        } else {
            Write-Host "MISSING: $f"
        }
    }
} else {
    Write-Host "`n[WARNING] No populated hf_models.db (>50KB) found to synchronize." -ForegroundColor Yellow
}

