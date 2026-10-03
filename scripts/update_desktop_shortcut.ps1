$wscript = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop "HugOS Browser.lnk"
$localApp = [System.Environment]::GetFolderPath('LocalApplicationData')
$appData = [System.Environment]::GetFolderPath('ApplicationData')
$startMenuLnk = Join-Path $appData "Microsoft\Windows\Start Menu\Programs\HugOS Browser\HugOS Browser.lnk"

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
    "D:\harfile\ModelFusion\IDE\hugos_browser.ico",
    "D:\harfile\ModelFusion\browser\ui\favicon.ico"
)
$iconPath = $iconCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($targetPath) {
    $workDir = Split-Path -Parent $targetPath
    foreach ($p in @($lnkPath, $startMenuLnk)) {
        if ($p -and (Test-Path (Split-Path -Parent $p))) {
            $shortcut = $wscript.CreateShortcut($p)
            $shortcut.TargetPath = $targetPath
            $shortcut.WorkingDirectory = $workDir
            if ($iconPath) {
                $shortcut.IconLocation = "$iconPath,0"
            }
            $shortcut.Description = "HugOS Browser - ModelFusion Local AI Web Environment"
            $shortcut.Save()
            Write-Output "Updated shortcut: $p -> $targetPath (Icon: $iconPath)"
        }
    }

    # Clear stale Chrome web app icon cache to force reload of radiant Gemini brain icon
    $cachedWebApps = Join-Path $localApp "HugOS Browser\User Data\Default\Web Applications"
    if (Test-Path $cachedWebApps) {
        Remove-Item -Path $cachedWebApps -Recurse -Force -ErrorAction SilentlyContinue
        Write-Output "Purged stale Web Applications icon cache from $cachedWebApps"
    }
    $cachedFavicons = Join-Path $localApp "HugOS Browser\User Data\Default\Favicons*"
    if (Test-Path $cachedFavicons) {
        Remove-Item -Path $cachedFavicons -Force -ErrorAction SilentlyContinue
        Write-Output "Purged stale Favicons cache"
    }
} else {
    Write-Error "No valid target found for shortcut."
}
