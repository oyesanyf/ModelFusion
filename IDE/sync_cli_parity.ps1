$src = "D:\harfile\ModelFusion\target\release\cli.exe"
$targets = @(
    "D:\harfile\ModelFusion\IDE\bin\cli.exe",
    "D:\harfile\ModelFusion\IDE\VSCode-win32-x64\bin\cli.exe",
    "$env:LOCALAPPDATA\HugOS IDE\bin\cli.exe",
    "D:\harfile\ModelFusion\browser\bin\cli.exe",
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
Write-Host "=== CRYPTOGRAPHIC 6-WAY PARITY VERIFICATION ==="
foreach ($f in $all) {
    if (Test-Path $f) {
        $h = (Get-FileHash -Path $f -Algorithm SHA256).Hash
        $s = (Get-Item $f).Length
        Write-Host "$h | $s bytes | $f"
    } else {
        Write-Host "MISSING: $f"
    }
}
