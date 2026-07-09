param(
    [Parameter(Mandatory = $true)][string]$GithubToken,
    [string]$Tag = "v1.0.0"
)

$repo = "oyesanyf/ModelFusion"
$msiPath = "D:\harfile\ModelFusion\IDE\HugOS.msi"
$cliPath = "D:\harfile\ModelFusion\target\release\cli.exe"

# Validate paths
if (-not (Test-Path $msiPath)) {
    Write-Error "MSI installer not found at $msiPath"
    exit 1
}
if (-not (Test-Path $cliPath)) {
    Write-Error "CLI binary not found at $cliPath"
    exit 1
}

$headers = @{
    "Authorization" = "token $GithubToken"
    "Accept"        = "application/vnd.github.v3+json"
    "User-Agent"    = "Powershell-Github-Uploader"
}

Write-Host "Creating GitHub Release for tag $Tag..."
$releaseBody = @{
    tag_name   = $Tag
    name       = "HugOS IDE $Tag"
    body       = "### HugOS IDE and CLI Tool Release`n`nCompiled binaries for HugOS IDE (VS Code Fork) and the ModelFusion CLI.`n`n- **HugOS.msi**: The main installer package.`n- **cli.exe**: The ModelFusion API orchestration server and CLI client."
    draft      = $false
    prerelease = $false
} | ConvertTo-Json -Depth 5

try {
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases" -Method Post -Body $releaseBody -Headers $headers -ContentType "application/json"
    $uploadUrl = $release.upload_url -replace '\{\?name,label\}', '?name='
    Write-Host "✅ Release created successfully: $($release.html_url)"
} catch {
    Write-Error "Failed to create release: $_"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Host "API Details: $($reader.ReadToEnd())"
    }
    exit 1
}

# Upload MSI
Write-Host "Uploading HugOS.msi..."
$msiBytes = [System.IO.File]::ReadAllBytes($msiPath)
$uploadMsiUrl = $uploadUrl + "HugOS.msi"
try {
    $msiAsset = Invoke-RestMethod -Uri $uploadMsiUrl -Method Post -Body $msiBytes -Headers $headers -ContentType "application/octet-stream"
    Write-Host "✅ Uploaded HugOS.msi!"
} catch {
    Write-Error "Failed to upload MSI: $_"
}

# Upload CLI
Write-Host "Uploading cli.exe..."
$cliBytes = [System.IO.File]::ReadAllBytes($cliPath)
$uploadCliUrl = $uploadUrl + "cli.exe"
try {
    $cliAsset = Invoke-RestMethod -Uri $uploadCliUrl -Method Post -Body $cliBytes -Headers $headers -ContentType "application/octet-stream"
    Write-Host "✅ Uploaded cli.exe!"
} catch {
    Write-Error "Failed to upload CLI: $_"
}

Write-Host "🎉 Release complete! View it at: $($release.html_url)"
