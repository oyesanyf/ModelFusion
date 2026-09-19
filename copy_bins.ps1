$src = "D:\harfile\ModelFusion\target\release\cli.exe"
if (-not (Test-Path $src)) {
    # Check gnu target output if not at default release dir
    $gnuSrc = "D:\harfile\ModelFusion\target\x86_64-pc-windows-gnu\release\cli.exe"
    if (Test-Path $gnuSrc) {
        Copy-Item -Path $gnuSrc -Destination $src -Force
    } else {
        Write-Error "Cannot find source cli.exe at $src or $gnuSrc"
        exit 1
    }
}

$destinations = @(
    "D:\harfile\ModelFusion\IDE\bin\cli.exe",
    "D:\harfile\ModelFusion\IDE\cli.exe",
    "D:\harfile\ModelFusion\IDE\VSCode-win32-x64\bin\cli.exe",
    (Join-Path $env:LOCALAPPDATA "HugOS IDE\bin\cli.exe")
)

$srcHash = (Get-FileHash -Path $src -Algorithm SHA256).Hash
Write-Host "[1/5] Source: $src"
Write-Host "      SHA256: $srcHash"

$count = 2
foreach ($dst in $destinations) {
    $parent = Split-Path -Parent $dst
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Copy-Item -Path $src -Destination $dst -Force
    $dstHash = (Get-FileHash -Path $dst -Algorithm SHA256).Hash
    $match = ($srcHash -eq $dstHash)
    Write-Host "[$count/5] Destination: $dst"
    Write-Host "      SHA256: $dstHash (Match: $match)"
    $count++
}

Write-Host "Binary mirroring complete across all 5 locations."
