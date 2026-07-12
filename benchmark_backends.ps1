$prompt = "What is the capital of Nigeria?"

Write-Host "Benchmarking Ollama..."
$ollama_time = Measure-Command {
    .\target\release\cli.exe --prompt $prompt --ollama
}

Write-Host "Benchmarking OpenVINO..."
$openvino_time = Measure-Command {
    .\target\release\cli.exe --prompt $prompt --openvino
}

Write-Host "------------------------------------------------"
Write-Host "Ollama Time: $($ollama_time.TotalSeconds) seconds"
Write-Host "OpenVINO Time: $($openvino_time.TotalSeconds) seconds"
Write-Host "------------------------------------------------"

if ($ollama_time.TotalSeconds -lt $openvino_time.TotalSeconds) {
    Write-Host "Winner: Ollama!"
} else {
    Write-Host "Winner: OpenVINO!"
}
