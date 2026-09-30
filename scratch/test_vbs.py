import subprocess
import time
import os

vbs = '''Set objShell = CreateObject("WScript.Shell")
Set args = WScript.Arguments
strCmd = Chr(34) & args(0) & Chr(34)
For i = 1 To args.Count - 1
    strCmd = strCmd & " " & Chr(34) & args(i) & Chr(34)
Next
WScript.Echo "CMD: " & strCmd
errCode = objShell.Run(strCmd, 0, False)
WScript.Echo "errCode: " & errCode
'''
with open('scratch/test_run.vbs', 'w') as f:
    f.write(vbs)

exe = r"C:\Users\oyesanyf\AppData\Local\HugOS Browser\bin\clibrowser.exe"
print("Exists:", os.path.exists(exe))

res = subprocess.run(['cscript', '//nologo', 'scratch/test_run.vbs', exe, '--server', '--port', '5000'], capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)

time.sleep(2)
res2 = subprocess.run(['powershell', '-NoProfile', '-Command', 'Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue'], capture_output=True, text=True)
print("TCP 5000:", res2.stdout)
