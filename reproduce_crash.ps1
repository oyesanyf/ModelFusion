$env:RUST_BACKTRACE = "1"
$port = 5999
$server = Start-Process -FilePath "D:\harfile\ModelFusion\target\release\cli.exe" -ArgumentList "--server", "--port", "$port", "--db-path", "D:\harfile\ModelFusion\IDE\db\hf_models.db" -PassThru -NoNewWindow
Start-Sleep -Seconds 2
try {
    $longCode = "adopt this code to crete quantum readiness code `r`n`r`n#!/usr/bin/env python3`r`n" + ("# quantum code sample line `r`n" * 500)
    $body = @{
        prompt = $longCode
        budget = 12
        selection_strategy = "multi_objective"
        fusion_mode = "multi-model"
        fusion_models = 10
        openvino = $false
        gpu = $true
        cpu = $false
        fusion = $false
        ollama = $true
        model = "qwen2.5:7b"
    } | ConvertTo-Json -Depth 5

    Write-Host "Sending POST request to port $port..."
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:$port/orchestrate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
    Write-Host "Success! Response length: $($res.content.Length)"
    Write-Host "Snippet: $($res.content.Substring(0, [Math]::Min(200, $res.content.Length)))"
} catch {
    Write-Host "Caught error: $($_.Exception.Message)"
} finally {
    Write-Host "Server exit code: $($server.ExitCode)"
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
}
