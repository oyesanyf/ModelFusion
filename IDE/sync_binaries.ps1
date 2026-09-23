$src = "target\release\cli.exe"
$targets = @(
    "IDE\bin\cli.exe",
    "IDE\VSCode-win32-x64\bin\cli.exe",
    "$env:LOCALAPPDATA\HugOS IDE\bin\cli.exe"
)

foreach ($dst in $targets) {
    $parent = Split-Path -Parent $dst
    if (!(Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Copy-Item -Path $src -Destination $dst -Force
    Write-Host "Copied $src to $dst"
}

$all = @($src) + $targets
Get-FileHash -Path $all -Algorithm SHA256 | Select-Object Path, Hash | Format-Table -AutoSize
