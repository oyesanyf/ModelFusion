' ModelFusion Master Server Background Daemon
Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
localApp = objShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")

candidates = Array( _
    localApp & "\HugOS Browser\bin\clibrowser.exe", _
    "D:\harfile\ModelFusion\browser\bin\clibrowser.exe", _
    "D:\harfile\ModelFusion\target\release\clibrowser.exe", _
    localApp & "\HugOS IDE\bin\cliide.exe", _
    "D:\harfile\ModelFusion\IDE\bin\cliide.exe", _
    localApp & "\HugOS Browser\bin\cli.exe", _
    localApp & "\HugOS IDE\bin\cli.exe", _
    "D:\harfile\ModelFusion\target\release\cli.exe", _
    localApp & "\Programs\ModelFusion\cli.exe" _
)

foundExe = ""
For Each candidate In candidates
    If fso.FileExists(candidate) Then
        foundExe = candidate
        Exit For
    End If
Next

If foundExe <> "" Then
    foundDir = fso.GetParentFolderName(foundExe)
    If fso.FolderExists(foundDir) Then
        objShell.CurrentDirectory = foundDir
    End If
    cmd = Chr(34) & foundExe & Chr(34) & " --server --port 5000"
    objShell.Run cmd, 0, False
End If
