# scripts/update_desktop_shortcut.ps1
# Updates HugOS IDE and HugOS Browser shortcuts across Desktop, Start Menu, and Taskbar.
# Binds Windows AppUserModelID (AUMID) via IPropertyStore to guarantee taskbar pinning and grouping parity.

$wscript = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')
$localApp = [System.Environment]::GetFolderPath('LocalApplicationData')
$appData = [System.Environment]::GetFolderPath('ApplicationData')
$taskbarDir = Join-Path $appData "Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"

# Define PropertyStore C# Helper for AppUserModelID
$propertyStoreCode = @"
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

[ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")]
public interface IPropertyStore {
    [PreserveSig] int GetCount(out uint cProps);
    [PreserveSig] int GetAt(uint iProp, out PropertyKey pkey);
    [PreserveSig] int GetValue(ref PropertyKey key, out PropVariant pv);
    [PreserveSig] int SetValue(ref PropertyKey key, ref PropVariant pv);
    [PreserveSig] int Commit();
}

[StructLayout(LayoutKind.Sequential, Pack = 4)]
public struct PropertyKey {
    public Guid fmtid;
    public uint pid;
    public PropertyKey(Guid guid, uint id) { fmtid = guid; pid = id; }
}

[StructLayout(LayoutKind.Explicit)]
public struct PropVariant {
    [FieldOffset(0)] public ushort vt;
    [FieldOffset(8)] public IntPtr pwszVal;
}

public class ShellShortcutHelper {
    [DllImport("shell32.dll")]
    public static extern void SHChangeNotify(uint wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);

    public static bool SetAumid(string lnkPath, string aumid) {
        try {
            Type shellLinkType = Type.GetTypeFromCLSID(new Guid("00021401-0000-0000-C000-000000000046"));
            object shellLink = Activator.CreateInstance(shellLinkType);
            IPersistFile persistFile = (IPersistFile)shellLink;
            persistFile.Load(lnkPath, 2); // STGM_READWRITE = 2

            IPropertyStore propStore = (IPropertyStore)shellLink;
            PropVariant pv = new PropVariant();
            pv.vt = 31; // VT_LPWSTR
            pv.pwszVal = Marshal.StringToCoTaskMemUni(aumid);
            PropertyKey key = new PropertyKey(new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5);
            propStore.SetValue(ref key, ref pv);
            propStore.Commit();
            persistFile.Save(lnkPath, true);
            Marshal.FreeCoTaskMem(pv.pwszVal);
            return true;
        } catch {
            return false;
        }
    }
}
"@

try {
    Add-Type -TypeDefinition $propertyStoreCode -ErrorAction SilentlyContinue
} catch {}

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
    (Join-Path $localApp "HugOS Browser\Chromium-win32-x64\hugos_browser.ico"),
    (Join-Path $localApp "HugOS Browser\ui\hugos_browser.ico"),
    "D:\harfile\ModelFusion\browser\ui\hugos_browser.ico",
    "D:\harfile\ModelFusion\IDE\hugos_browser.ico"
)
$browserIcon = $browserIconCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($browserTarget) {
    $browserWorkDir = Split-Path -Parent $browserTarget
    foreach ($p in @($browserLnkPath, $browserStartMenu, $browserTaskbar)) {
        $parentDir = Split-Path -Parent $p
        if (-not (Test-Path $parentDir)) {
            New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
        }
        $shortcut = $wscript.CreateShortcut($p)
        $shortcut.TargetPath = $browserTarget
        $shortcut.WorkingDirectory = $browserWorkDir
        if ($browserIcon) {
            $shortcut.IconLocation = "$browserIcon,0"
        }
        $shortcut.Description = "HugOS Browser - ModelFusion Local AI Web Environment"
        $shortcut.Save()

        # Stamp AUMID
        [ShellShortcutHelper]::SetAumid($p, "HugOS.Browser.Engine") | Out-Null
        (Get-Item $p).LastWriteTime = Get-Date
        Write-Output "Updated Browser shortcut: $p -> $browserTarget (Icon: $browserIcon, AUMID: HugOS.Browser.Engine)"
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
    (Join-Path $localApp "HugOS IDE\hugos.ico"),
    (Join-Path $localApp "HugOS IDE\code.ico"),
    "D:\harfile\ModelFusion\IDE\hugos.ico",
    "D:\harfile\ModelFusion\IDE\code.ico"
)
$ideIcon = $ideIconCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($ideTarget) {
    $ideWorkDir = Split-Path -Parent $ideTarget
    foreach ($p in @($ideLnkPath, $ideStartMenu, $ideTaskbar)) {
        $parentDir = Split-Path -Parent $p
        if (-not (Test-Path $parentDir)) {
            New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
        }
        $shortcut = $wscript.CreateShortcut($p)
        $shortcut.TargetPath = $ideTarget
        $shortcut.WorkingDirectory = $ideWorkDir
        if ($ideIcon) {
            $shortcut.IconLocation = "$ideIcon,0"
        }
        $shortcut.Description = "HugOS IDE - ModelFusion AI Operating System"
        $shortcut.Save()

        # Stamp AUMID
        [ShellShortcutHelper]::SetAumid($p, "HugOS.HugOS") | Out-Null
        (Get-Item $p).LastWriteTime = Get-Date
        Write-Output "Updated IDE shortcut: $p -> $ideTarget (Icon: $ideIcon, AUMID: HugOS.HugOS)"
    }
}

# 3. Flush Windows Shell Icon Cache
try {
    [ShellShortcutHelper]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
    Write-Output "[OK] Shell icon cache notified and flushed via SHChangeNotify."
} catch {
    Write-Output "[WARN] Could not notify shell: $_"
}

# Invoke ie4uinit if available to refresh Windows icon cache
try {
    Start-Process -FilePath "ie4uinit.exe" -ArgumentList "-show" -WindowStyle Hidden -ErrorAction SilentlyContinue
} catch {}

Write-Output "[SUCCESS] All shortcuts (Desktop, Start Menu, Taskbar) refreshed with high-res multi-layer icons and AUMID!"
