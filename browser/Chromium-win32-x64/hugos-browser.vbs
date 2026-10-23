' hugos-browser.vbs - Direct Zero-Console GUI Launcher for HugOS Browser
' Launches an instant visual loading splash (<60ms) and spawns the Chromium GUI
' directly with WindowStyle = 1 (SW_SHOWNORMAL) without ever creating a cmd.exe window.
Option Explicit

Dim objShell, fso, strScriptDir, strRootDir, localApp, progFiles, progFiles86
Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
strRootDir = fso.GetParentFolderName(strScriptDir)
localApp = objShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
progFiles = objShell.ExpandEnvironmentStrings("%ProgramFiles%")
progFiles86 = objShell.ExpandEnvironmentStrings("%ProgramFiles(x86)%")

' 1. Instant Visual Splash Screen (<60ms feedback on double-click)
Dim splashPath
splashPath = strScriptDir & "\hugos-splash.hta"
If fso.FileExists(splashPath) Then
    On Error Resume Next
    objShell.Run "mshta.exe " & Chr(34) & splashPath & Chr(34), 1, False
    On Error GoTo 0
End If

' 2. Resolve Startup URL (genuine HugOS Browser UI via file:/// protocol)
Dim defaultHome, startUrl, extensionDir, userDataDir
defaultHome = strRootDir & "\ui\index.html"
If Not fso.FileExists(defaultHome) Then
    If fso.FileExists(localApp & "\HugOS Browser\ui\index.html") Then
        defaultHome = localApp & "\HugOS Browser\ui\index.html"
    End If
End If
defaultHome = fso.GetAbsolutePathName(defaultHome)
startUrl = "file:///" & Replace(defaultHome, "\", "/")

If WScript.Arguments.Count > 0 Then
    If Trim(WScript.Arguments(0)) <> "" Then
        startUrl = WScript.Arguments(0)
    End If
End If

extensionDir = fso.GetAbsolutePathName(strRootDir & "\extension")
userDataDir = localApp & "\HugOS Browser\User Data"
If Not fso.FolderExists(localApp & "\HugOS Browser") Then
    On Error Resume Next
    fso.CreateFolder(localApp & "\HugOS Browser")
    On Error GoTo 0
End If
If Not fso.FolderExists(userDataDir) Then
    On Error Resume Next
    fso.CreateFolder(userDataDir)
    On Error GoTo 0
End If

' 3. Discover Chromium / Google Chrome / Microsoft Edge Binary
Dim chromeCandidates, candidate, chromeBin
chromeCandidates = Array( _
    strScriptDir & "\chrome.exe", _
    strScriptDir & "\chromium.exe", _
    progFiles & "\Google\Chrome\Application\chrome.exe", _
    progFiles86 & "\Google\Chrome\Application\chrome.exe", _
    localApp & "\Google\Chrome\Application\chrome.exe", _
    progFiles86 & "\Microsoft\Edge\Application\msedge.exe", _
    progFiles & "\Microsoft\Edge\Application\msedge.exe" _
)

chromeBin = ""
For Each candidate In chromeCandidates
    If fso.FileExists(candidate) Then
        chromeBin = candidate
        Exit For
    End If
Next

If chromeBin <> "" Then
    Dim chromeCmd
    chromeCmd = Chr(34) & chromeBin & Chr(34) & _
        " --app=" & Chr(34) & startUrl & Chr(34) & _
        " --new-window" & _
        " --remote-debugging-port=9222" & _
        " --remote-allow-origins=*" & _
        " --load-extension=" & Chr(34) & extensionDir & Chr(34) & _
        " --user-data-dir=" & Chr(34) & userDataDir & Chr(34) & _
        " --enable-gpu-rasterization --enable-zero-copy --ignore-gpu-blocklist" & _
        " --disable-renderer-backgrounding --disable-background-timer-throttling" & _
        " --enable-smooth-scrolling --disable-backgrounding-occluded-windows" & _
        " --no-first-run --no-default-browser-check" & _
        " --enable-features=SidePanel,SidePanelPinning,CanvasOopRasterization" & _
        " --disable-features=Translate,OptimizationHints --disk-cache-size=104857600"

    ' Launch Browser directly as a normal visible foreground window (1 = SW_SHOWNORMAL), ZERO cmd.exe!
    objShell.Run chromeCmd, 1, False
End If

' 4. Non-blocking Background Daemon Verification (clibrowser.exe --server & --ensure-ollama)
Dim cliCandidates, cliBin, cliDir
cliCandidates = Array( _
    strRootDir & "\bin\clibrowser.exe", _
    localApp & "\HugOS Browser\bin\clibrowser.exe", _
    "D:\harfile\ModelFusion\target\release\clibrowser.exe", _
    strRootDir & "\bin\cli.exe", _
    localApp & "\HugOS Browser\bin\cli.exe", _
    "D:\harfile\ModelFusion\target\release\cli.exe" _
)

cliBin = ""
For Each candidate In cliCandidates
    If fso.FileExists(candidate) Then
        cliBin = candidate
        Exit For
    End If
Next

If cliBin <> "" Then
    cliDir = fso.GetParentFolderName(cliBin)
    If fso.FolderExists(cliDir) Then
        objShell.CurrentDirectory = cliDir
    End If
    On Error Resume Next
    objShell.Run Chr(34) & cliBin & Chr(34) & " --server --port 5000", 0, False
    objShell.Run Chr(34) & cliBin & Chr(34) & " --ensure-ollama", 0, False
    On Error GoTo 0
End If
