Set WshShell = WScript.CreateObject("WScript.Shell")
titles = Array("LinkedIn", "Google Chrome", "Chrome", "Ahura", "Apply")
activated = False
For Each t In titles
    If WshShell.AppActivate(t) Then
        WScript.Echo "Successfully activated window matching: " & t
        activated = True
        Exit For
    End If
Next

If Not activated Then
    WScript.Echo "Failed to activate any window."
Else
    WScript.Sleep 500
    ' Send TAB to focus Next button, then ENTER
    WshShell.SendKeys "{TAB}"
    WScript.Sleep 200
    WshShell.SendKeys "{ENTER}"
    WScript.Echo "Sent TAB + ENTER to advanced form!"
End If
