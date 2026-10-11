Set WshShell = WScript.CreateObject("WScript.Shell")
WshShell.AppActivate "Chrome"
WScript.Sleep 500
WshShell.SendKeys "{ENTER}"
