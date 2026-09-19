$src = "D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\extension.js"
if (-not (Test-Path $src)) {
    Write-Error "Source file does not exist: $src"
    exit 1
}

$srcHash = (Get-FileHash -Path $src -Algorithm SHA256).Hash
Write-Host "Source Hash: $srcHash"

$targets = @(
    "D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
    (Join-Path $env:LOCALAPPDATA "HugOS IDE\resources\app\extensions\copilot\dist\extension.js"),
    (Join-Path $env:LOCALAPPDATA "HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js")
)

foreach ($t in $targets) {
    $parentDir = Split-Path -Parent $t
    if (Test-Path $parentDir) {
        Copy-Item -Path $src -Destination $t -Force
        $destHash = (Get-FileHash -Path $t -Algorithm SHA256).Hash
        Write-Host "Synchronized $t"
        Write-Host "  -> Hash: $destHash (Match: $($srcHash -eq $destHash))"
    } else {
        Write-Host "Parent directory not found for $t (skipping)"
    }
}
