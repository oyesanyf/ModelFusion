' hugos-browser.vbs - Silent GUI launcher for HugOS Browser
Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = Chr(34) & strScriptDir & "\hugos-browser.bat" & Chr(34)
For i = 0 To WScript.Arguments.Count - 1
    batPath = batPath & " " & Chr(34) & WScript.Arguments(i) & Chr(34)
Next
objShell.Run batPath, 0, False
