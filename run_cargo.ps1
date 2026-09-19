$mingwBin = "C:\Users\oyesanyf\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.MSVCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin"
$env:PATH = "$mingwBin;" + $env:PATH
cargo +stable-x86_64-pc-windows-gnu @args
