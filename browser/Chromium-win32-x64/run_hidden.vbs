' run_hidden.vbs - Executes target command with hidden window (0, False)
Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Set args = WScript.Arguments

Function CleanQuote(s)
    Dim trimmed
    trimmed = Trim(s)
    If Left(trimmed, 1) = Chr(34) And Right(trimmed, 1) = Chr(34) And Len(trimmed) >= 2 Then
        trimmed = Mid(trimmed, 2, Len(trimmed) - 2)
    End If
    CleanQuote = Chr(34) & trimmed & Chr(34)
End Function

If args.Count > 0 Then
    If fso.FileExists(args(0)) Then
        parentFolder = fso.GetParentFolderName(args(0))
        If parentFolder <> "" Then
            objShell.CurrentDirectory = parentFolder
        End If
    End If
    strCmd = CleanQuote(args(0))
    For i = 1 To args.Count - 1
        strCmd = strCmd & " " & CleanQuote(args(i))
    Next
    objShell.Run strCmd, 0, False
End If
