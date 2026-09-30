$env:PATH = "C:\Program Files\LLVM\bin;C:\Users\oyesanyf\.cargo\bin;" + $env:PATH
$env:CC = "clang-cl"
$env:AR = "llvm-lib"
$env:INCLUDE = "D:\tools\xwin-crt\crt\include;D:\tools\xwin-crt\sdk\include\ucrt;D:\tools\xwin-crt\sdk\include\um;D:\tools\xwin-crt\sdk\include\shared"
$env:LIB = "D:\tools\xwin-crt\crt\lib\x64;D:\tools\xwin-crt\sdk\lib\um\x64;D:\tools\xwin-crt\sdk\lib\ucrt\x64"
& "C:\Users\oyesanyf\.cargo\bin\cargo.exe" @args
