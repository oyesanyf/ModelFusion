$wscript = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop "HugOS Browser.lnk"
$localApp = [System.Environment]::GetFolderPath('LocalApplicationData')

$targetVbsCandidates = @(
    (Join-Path $localApp "HugOS Browser\Chromium-win32-x64\hugos-browser.vbs"),
    "D:\harfile\ModelFusion\browser\Chromium-win32-x64\hugos-browser.vbs",
    (Join-Path $localApp "HugOS Browser\Chromium-win32-x64\hugos-browser.bat"),
    "D:\harfile\ModelFusion\browser\Chromium-win32-x64\hugos-browser.bat"
)
$targetPath = $targetVbsCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

$iconCandidates = @(
    "D:\harfile\ModelFusion\browser\ui\hugos_browser.ico",
    (Join-Path $localApp "HugOS Browser\ui\hugos_browser.ico"),
    "D:\harfile\ModelFusion\IDE\hugos_browser.ico"
)
$iconPath = $iconCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($targetPath) {
    $workDir = Split-Path -Parent $targetPath
    $shortcut = $wscript.CreateShortcut($lnkPath)
    $shortcut.TargetPath = $targetPath
    $shortcut.WorkingDirectory = $workDir
    if ($iconPath) {
        $shortcut.IconLocation = "$iconPath,0"
    }
    $shortcut.Description = "HugOS Browser - ModelFusion Local AI Web Environment"
    $shortcut.Save()
    Write-Output "Updated shortcut: $lnkPath -> $targetPath (Icon: $iconPath)"
} else {
    Write-Error "No valid target found for shortcut."
}
