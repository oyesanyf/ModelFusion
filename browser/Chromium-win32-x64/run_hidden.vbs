' run_hidden.vbs - Executes target command with hidden window (0, False)
Set objShell = CreateObject("WScript.Shell")
Set args = WScript.Arguments
If args.Count > 0 Then
    strCmd = Chr(34) & args(0) & Chr(34)
    For i = 1 To args.Count - 1
        strCmd = strCmd & " " & Chr(34) & args(i) & Chr(34)
    Next
    objShell.Run strCmd, 0, False
End If
