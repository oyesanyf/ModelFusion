$base = "C:\Users\oyesa\AppData\Local\HugOS IDE\resources\app\extensions"
$copilot = Join-Path $base "copilot"
$mf = Join-Path $base "modelfusion"

if (Test-Path $copilot) {
    if (Test-Path $mf) { Remove-Item $mf -Recurse -Force }
    Rename-Item $copilot "modelfusion" -Force
    Write-Host "1. Renamed copilot -> modelfusion"
} else {
    Write-Host "1. copilot dir not found (may already be renamed)"
}

Copy-Item -Path "d:\harfile\ModelFusion\IDE\vscode\extensions\modelfusion\dist\*" -Destination (Join-Path $mf "dist") -Force -Recurse
Copy-Item -Path "d:\harfile\ModelFusion\IDE\vscode\extensions\modelfusion\package.json" -Destination (Join-Path $mf "package.json") -Force
Write-Host "2. Deployed updated dist + package.json"

Copy-Item -Path "d:\harfile\ModelFusion\IDE\vscode\product.json" -Destination "C:\Users\oyesa\AppData\Local\HugOS IDE\resources\app\product.json" -Force
Write-Host "3. Deployed updated product.json"

Copy-Item -Path "d:\harfile\ModelFusion\IDE\hugos.ico" -Destination "C:\Users\oyesa\AppData\Local\HugOS IDE\resources\app\resources\win32\code.ico" -Force
Write-Host "4. Deployed new brain icon"

Write-Host "Done! Launch HugOS IDE."
