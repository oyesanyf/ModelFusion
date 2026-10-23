' hugos-browser.vbs - Direct Zero-Console GUI Launcher for HugOS Browser
' Launches an instant visual loading splash (<60ms), brings or opens the single
' HugOS Browser GUI window to foreground z-order #1, and starts background daemons
' with zero visible cmd.exe or console windows.
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

' 2. Discover ModelFusion Browser CLI Binary (clibrowser.exe priority per Browser Law)
Dim cliCandidates, candidate, cliBin, cliDir
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

' 3. Resolve Startup URL (genuine HugOS Browser UI via file:/// protocol)
Dim defaultHome, startUrl, hasCustomUrl, extensionDir, userDataDir
defaultHome = strRootDir & "\ui\index.html"
If Not fso.FileExists(defaultHome) Then
    If fso.FileExists(localApp & "\HugOS Browser\ui\index.html") Then
        defaultHome = localApp & "\HugOS Browser\ui\index.html"
    End If
End If
defaultHome = fso.GetAbsolutePathName(defaultHome)
startUrl = "file:///" & Replace(defaultHome, "\", "/")
hasCustomUrl = False

If WScript.Arguments.Count > 0 Then
    If Trim(WScript.Arguments(0)) <> "" Then
        startUrl = WScript.Arguments(0)
        hasCustomUrl = True
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

' 4. Check if HugOS Browser window is already open (avoid opening duplicate windows)
Dim alreadyOpen
alreadyOpen = False
If cliBin <> "" And Not hasCustomUrl Then
    On Error Resume Next
    If objShell.Run(Chr(34) & cliBin & Chr(34) & " --check-browser-window", 0, True) = 0 Then
        alreadyOpen = True
    End If
    On Error GoTo 0
End If

' 5. Discover Chromium / Google Chrome / Microsoft Edge Binary & Launch if needed
If Not alreadyOpen Then
    Dim chromeCandidates, chromeBin
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

        ' Launch Browser directly as a normal visible window (1 = SW_SHOWNORMAL), ZERO cmd.exe!
        objShell.Run chromeCmd, 1, False
    End If
End If

' 6. Coordinate Splash -> Foreground Promotion (z-order #1) & Non-blocking Background Daemons
If cliBin <> "" Then
    cliDir = fso.GetParentFolderName(cliBin)
    If fso.FolderExists(cliDir) Then
        objShell.CurrentDirectory = cliDir
    End If
    On Error Resume Next
    objShell.Run Chr(34) & cliBin & Chr(34) & " --focus-browser", 0, False
    objShell.Run Chr(34) & cliBin & Chr(34) & " --server --port 5000", 0, False
    objShell.Run Chr(34) & cliBin & Chr(34) & " --ensure-ollama", 0, False
    On Error GoTo 0
End If
