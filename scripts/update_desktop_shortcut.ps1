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

    try {
        $code = @"
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

public class ShortcutHelper {
    public static void SetAppUserModelId(string lnkPath, string aumid) {
        Type shellLinkType = Type.GetTypeFromCLSID(new Guid("00021401-0000-0000-C000-000000000046"));
        object shellLink = Activator.CreateInstance(shellLinkType);
        IPersistFile persistFile = (IPersistFile)shellLink;
        persistFile.Load(lnkPath, 0);

        IPropertyStore propStore = (IPropertyStore)shellLink;
        PropVariant pv = new PropVariant();
        pv.vt = 31;
        pv.pwszVal = Marshal.StringToCoTaskMemUni(aumid);
        PropertyKey key = new PropertyKey(new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5);
        propStore.SetValue(ref key, ref pv);
        propStore.Commit();
        persistFile.Save(lnkPath, true);
        Marshal.FreeCoTaskMem(pv.pwszVal);
    }
}
"@
        Add-Type -TypeDefinition $code -ErrorAction SilentlyContinue
        [ShortcutHelper]::SetAppUserModelId($lnkPath, "HugOS.Browser.Engine")
        Write-Output "Set AppUserModelId: HugOS.Browser.Engine on $lnkPath"
    } catch {
        Write-Warning "Could not set AppUserModelId: $_"
    }
} else {
    Write-Error "No valid target found for shortcut."
}
