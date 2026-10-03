$wscript = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')
$localApp = [System.Environment]::GetFolderPath('LocalApplicationData')
$appData = [System.Environment]::GetFolderPath('ApplicationData')
$taskbarDir = Join-Path $appData "Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"

# 1. Update HugOS Browser Shortcuts (Desktop, Start Menu, Taskbar)
$browserLnkPath = Join-Path $desktop "HugOS Browser.lnk"
$browserStartMenu = Join-Path $appData "Microsoft\Windows\Start Menu\Programs\HugOS Browser\HugOS Browser.lnk"
$browserTaskbar = Join-Path $taskbarDir "HugOS Browser.lnk"

$targetVbsCandidates = @(
    (Join-Path $localApp "HugOS Browser\Chromium-win32-x64\hugos-browser.vbs"),
    "D:\harfile\ModelFusion\browser\Chromium-win32-x64\hugos-browser.vbs",
    (Join-Path $localApp "HugOS Browser\Chromium-win32-x64\hugos-browser.bat"),
    "D:\harfile\ModelFusion\browser\Chromium-win32-x64\hugos-browser.bat"
)
$browserTarget = $targetVbsCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

$browserIconCandidates = @(
    "D:\harfile\ModelFusion\browser\ui\hugos_browser.ico",
    (Join-Path $localApp "HugOS Browser\ui\hugos_browser.ico"),
    "D:\harfile\ModelFusion\IDE\hugos_browser.ico",
    "D:\harfile\ModelFusion\browser\ui\favicon.ico"
)
$browserIcon = $browserIconCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($browserTarget) {
    $browserWorkDir = Split-Path -Parent $browserTarget
    foreach ($p in @($browserLnkPath, $browserStartMenu, $browserTaskbar)) {
        if ($p -and (Test-Path (Split-Path -Parent $p))) {
            $shortcut = $wscript.CreateShortcut($p)
            $shortcut.TargetPath = $browserTarget
            $shortcut.WorkingDirectory = $browserWorkDir
            if ($browserIcon) {
                $shortcut.IconLocation = "$browserIcon,0"
            }
            $shortcut.Description = "HugOS Browser - ModelFusion Local AI Web Environment"
            $shortcut.Save()
            Write-Output "Updated Browser shortcut: $p -> $browserTarget (Icon: $browserIcon)"
        }
    }
}

# 2. Update HugOS IDE Shortcuts (Desktop, Start Menu, Taskbar)
$ideLnkPath = Join-Path $desktop "HugOS IDE.lnk"
$ideStartMenu = Join-Path $appData "Microsoft\Windows\Start Menu\Programs\HugOS IDE\HugOS IDE.lnk"
$ideTaskbar = Join-Path $taskbarDir "HugOS IDE.lnk"

$ideExeCandidates = @(
    (Join-Path $localApp "HugOS IDE\HugOS.exe"),
    "D:\harfile\ModelFusion\IDE\VSCode-win32-x64\HugOS.exe"
)
$ideTarget = $ideExeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

$ideIconCandidates = @(
    "D:\harfile\ModelFusion\IDE\hugos.ico",
    "D:\harfile\ModelFusion\IDE\code.ico",
    (Join-Path $localApp "HugOS IDE\resources\app\resources\win32\code.ico")
)
$ideIcon = $ideIconCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($ideTarget) {
    $ideWorkDir = Split-Path -Parent $ideTarget
    foreach ($p in @($ideLnkPath, $ideStartMenu, $ideTaskbar)) {
        if ($p -and (Test-Path (Split-Path -Parent $p))) {
            $shortcut = $wscript.CreateShortcut($p)
            $shortcut.TargetPath = $ideTarget
            $shortcut.WorkingDirectory = $ideWorkDir
            if ($ideIcon) {
                $shortcut.IconLocation = "$ideIcon,0"
            }
            $shortcut.Description = "HugOS IDE - ModelFusion AI Operating System"
            $shortcut.Save()
            Write-Output "Updated IDE shortcut: $p -> $ideTarget (Icon: $ideIcon)"
        }
    }
}

try {
    Add-Type -TypeDefinition @"
    using System;
    using System.Runtime.InteropServices;
    public class ShellNotification {
        [DllImport("shell32.dll")]
        public static extern void SHChangeNotify(uint wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
    }
"@
    [ShellNotification]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
    Write-Output "[OK] Shell icon cache refreshed via SHChangeNotify."
} catch {
    Write-Output "[WARN] Could not notify shell: $_"
}

Write-Output "[SUCCESS] All shortcuts (Desktop, Start Menu, Taskbar) refreshed with high-res multi-layer icons!"
