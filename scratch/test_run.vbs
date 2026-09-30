Set objShell = CreateObject("WScript.Shell")
Set args = WScript.Arguments
strCmd = Chr(34) & args(0) & Chr(34)
For i = 1 To args.Count - 1
    strCmd = strCmd & " " & Chr(34) & args(i) & Chr(34)
Next
WScript.Echo "CMD: " & strCmd
errCode = objShell.Run(strCmd, 0, False)
WScript.Echo "errCode: " & errCode
