# Setup script for IDE/patches directory
# Creates icon directories and copies binary icon files

$root = "d:\harfile\ModelFusion"

# Step 1: Create directories
New-Item -ItemType Directory -Path "$root\IDE\patches\icons\win32" -Force | Out-Null
New-Item -ItemType Directory -Path "$root\IDE\patches\icons\darwin" -Force | Out-Null
New-Item -ItemType Directory -Path "$root\IDE\patches\icons\linux" -Force | Out-Null

# Step 2: Copy icon files
Copy-Item -Path "$root\IDE\hugos.ico" -Destination "$root\IDE\patches\icons\win32\code.ico" -Force
Copy-Item -Path "$root\IDE\vscode\resources\win32\code_150x150.png" -Destination "$root\IDE\patches\icons\win32\code_150x150.png" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$root\IDE\vscode\resources\win32\code_70x70.png" -Destination "$root\IDE\patches\icons\win32\code_70x70.png" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$root\IDE\vscode\resources\darwin\code.icns" -Destination "$root\IDE\patches\icons\darwin\code.icns" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$root\IDE\vscode\resources\linux\code.png" -Destination "$root\IDE\patches\icons\linux\code.png" -Force -ErrorAction SilentlyContinue

Write-Host "Done! Listing patches directory:"
Get-ChildItem -Recurse "$root\IDE\patches"
