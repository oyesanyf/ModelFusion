# HugOS IDE Signed MSI Packaging Script
# This script compiles, copies cli.exe, signs all binaries, generates a WiX manifest, and builds/signs the final MSI.

$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$vsCodePackDir = Join-Path (Split-Path $PSScriptRoot -Parent) "IDE\VSCode-win32-x64"
$pfxPath = Join-Path $PSScriptRoot "hugos-signing-cert.pfx"
$password = "HugOSPassword123!"

Write-Host "--------------------------------------------------------" -ForegroundColor Green
Write-Host "[START] Starting HugOS IDE Signed MSI Packaging Process" -ForegroundColor Green
Write-Host "--------------------------------------------------------" -ForegroundColor Green

# 1. Verify VSCode-win32-x64 directory exists
if (-not (Test-Path $vsCodePackDir)) {
    Write-Host "[ERROR] Packaged directory not found at: $vsCodePackDir" -ForegroundColor Red
    Write-Host "Please make sure the gulp package task (vscode-win32-x64) has finished." -ForegroundColor Yellow
    Exit 1
}
Write-Host "[OK] Resolved packaged VS Code directory at $vsCodePackDir" -ForegroundColor Green

# 2. Locate signtool.exe
$signtoolPath = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
if (-not (Test-Path $signtoolPath)) {
    Write-Host "[INFO] Signtool not found at default path, searching Windows Kits..." -ForegroundColor Yellow
    $signtoolPath = Get-ChildItem -Path 'C:\Program Files (x86)\Windows Kits' -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue | 
                    Where-Object { $_.FullName -like "*x64*" } | 
                    Select-Object -ExpandProperty FullName -First 1
}

if (-not $signtoolPath) {
    Write-Host "[ERROR] signtool.exe could not be found on this system. Please install the Windows SDK." -ForegroundColor Red
    Exit 1
}
Write-Host "[OK] Using signtool at: $signtoolPath" -ForegroundColor Green

# 3. Code Signing Certificate Setup
if (-not (Test-Path $pfxPath)) {
    Write-Host "[INFO] Creating a self-signed code signing certificate..." -ForegroundColor Yellow
    
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=HugOS IDE" -FriendlyName "HugOS Code Signing" -CertStoreLocation "Cert:\CurrentUser\My"
    $pwdSecure = ConvertTo-SecureString $password -AsPlainText -Force
    Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pwdSecure
    
    Write-Host "[OK] Certificate created at: $pfxPath" -ForegroundColor Green
} else {
    Write-Host "[OK] Found existing signing certificate at $pfxPath" -ForegroundColor Green
}

# 4. Copy ModelFusion CLI (cli.exe) into the packaged folder
$cliSrcPath = Join-Path (Split-Path $PSScriptRoot -Parent) "target\release\cli.exe"
if (-not (Test-Path $cliSrcPath)) {
    Write-Host "[ERROR] ModelFusion cli.exe not found at $cliSrcPath. Run 'cargo build --release' first." -ForegroundColor Red
    Exit 1
}

$cliDestDir = Join-Path $vsCodePackDir "bin"
if (-not (Test-Path $cliDestDir)) {
    New-Item -ItemType Directory -Force -Path $cliDestDir | Out-Null
}

$cliDestPath = Join-Path $cliDestDir "cli.exe"
Copy-Item -Path $cliSrcPath -Destination $cliDestPath -Force
Write-Host "[OK] Copied ModelFusion CLI to: $cliDestPath" -ForegroundColor Green

# 4.1 Restore original Electron binary (Code.exe -> HugOS.exe)
# CRITICAL: Do NOT use the custom-built HugOS.exe here — it was compiled with a modified
# Electron resource table that breaks ICU data loading after any code signing.
# Instead, download the matching VSCode 1.126.0 release and use Code.exe verbatim.
# The HugOS branding is controlled entirely by product.json, NOT the binary.
$hugosExePath = Join-Path $vsCodePackDir "HugOS.exe"
$vscodeDlZip  = Join-Path $PSScriptRoot "vscode-1.126.0-win32-x64.zip"
$vscodeDlUrl  = "https://update.code.visualstudio.com/1.126.0/win32-x64-archive/stable"

# Check if current HugOS.exe has a valid (Microsoft) signature
$exeSig = Get-AuthenticodeSignature $hugosExePath -ErrorAction SilentlyContinue
if ($exeSig.Status -ne 'Valid' -or $exeSig.SignerCertificate.Subject -notlike '*Microsoft*') {
    Write-Host "[INFO] HugOS.exe has invalid/untrusted signature. Restoring from VSCode 1.126.0..." -ForegroundColor Yellow
    if (-not (Test-Path $vscodeDlZip) -or (Get-Item $vscodeDlZip).Length -lt 100MB) {
        Write-Host "[INFO] Downloading VSCode 1.126.0 (~280MB)..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $vscodeDlUrl -OutFile $vscodeDlZip -UseBasicParsing
    }
    $extractDir = Join-Path $env:TEMP "vscode-126-restore"
    Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive -Path $vscodeDlZip -DestinationPath $extractDir -Force

    # Replace HugOS.exe with Code.exe (same Electron, valid Microsoft signature)
    $codeExeFile = Get-ChildItem $extractDir -Filter "Code.exe" -Recurse | Select-Object -First 1
    Copy-Item $codeExeFile.FullName $hugosExePath -Force
    Write-Host "[OK] HugOS.exe restored from Code.exe ($([int]($codeExeFile.Length/1MB)) MB, valid Microsoft sig)" -ForegroundColor Green

    # Also sync matching Electron runtime data files (root-level copies)
    foreach ($f in @('icudtl.dat','v8_context_snapshot.bin','snapshot_blob.bin')) {
        $src = Get-ChildItem $extractDir -Filter $f -Recurse | Select-Object -First 1
        if ($src) { Copy-Item $src.FullName (Join-Path $vsCodePackDir $f) -Force }
    }

    # CRITICAL: Copy the versioned Electron runtime directory (e.g. 7e7950df89/).
    # Code.exe loads ICU data from this subdirectory, NOT from root.
    # Without it, HugOS.exe crashes with "Invalid file descriptor to ICU data received".
    $versionedDir = Get-ChildItem $extractDir -Directory | Where-Object { $_.Name -match '^[0-9a-f]{10,}$' } | Select-Object -First 1
    if ($versionedDir) {
        $destVersionedDir = Join-Path $vsCodePackDir $versionedDir.Name
        Copy-Item $versionedDir.FullName $destVersionedDir -Recurse -Force
        Write-Host "[OK] Copied Electron versioned runtime directory: $($versionedDir.Name)/" -ForegroundColor Green

        # CRITICAL: Replace the versioned dir's product.json with HugOS branding.
        # The VSCode zip ships with product.json containing nameShort:"Code" / nameLong:"Visual Studio Code"
        # which OVERRIDES our resources/app/product.json and makes the IDE show VSCode branding.
        $versionedProductJson = Join-Path $destVersionedDir "resources\app\product.json"
        $hugosProductJson = Join-Path $vsCodePackDir "resources\app\product.json"
        if ((Test-Path $versionedProductJson) -and (Test-Path $hugosProductJson)) {
            Copy-Item $hugosProductJson $versionedProductJson -Force
            Write-Host "[OK] Replaced versioned product.json with HugOS branding" -ForegroundColor Green
        }

        # CRITICAL: Copy modelfusion extension into the versioned directory.
        # The versioned dir has its own complete extensions/ folder (96 stock extensions)
        # but does NOT contain modelfusion. Without this, the IDE uses GitHub Copilot
        # chat instead of our custom ModelFusion AI chat.
        $mfExtSrc = Join-Path $vsCodePackDir "resources\app\extensions\modelfusion"
        $mfExtDest = Join-Path $destVersionedDir "resources\app\extensions\modelfusion"
        if (Test-Path $mfExtSrc) {
            Copy-Item $mfExtSrc $mfExtDest -Recurse -Force
            Write-Host "[OK] Copied modelfusion extension to versioned directory" -ForegroundColor Green
        }
    } else {
        Write-Host "[WARNING] No versioned runtime directory found in VSCode zip!" -ForegroundColor Yellow
    }

    Write-Host "[OK] Electron runtime data files synced" -ForegroundColor Green
    Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "[OK] HugOS.exe already has valid Microsoft signature - no restore needed" -ForegroundColor Green
}

# 4.5 Copy Pre-populated HF Models Database (hf_models.db) into the packaged folder
$dbSrcPath = Join-Path (Split-Path $PSScriptRoot -Parent) "db\hf_models.db"
if (Test-Path $dbSrcPath) {
    $dbDestDir = Join-Path $vsCodePackDir "db"
    if (-not (Test-Path $dbDestDir)) {
        New-Item -ItemType Directory -Force -Path $dbDestDir | Out-Null
    }
    $dbDestPath = Join-Path $dbDestDir "hf_models.db"
    Write-Host "[INFO] Copying pre-populated models database to installer package (this may take a few seconds)..." -ForegroundColor Yellow
    Copy-Item -Path $dbSrcPath -Destination $dbDestPath -Force
    Write-Host "[OK] Copied ModelFusion Database to: $dbDestPath" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Pre-populated database not found at $dbSrcPath. Packaging without pre-populated DB." -ForegroundColor Yellow
}
# 4.6 Copy Python helper scripts into the packaged folder
$scriptsSrcPath = Join-Path (Split-Path $PSScriptRoot -Parent) "src\scripts"
if (Test-Path $scriptsSrcPath) {
    $scriptsDestDir = Join-Path $vsCodePackDir "src\scripts"
    if (-not (Test-Path $scriptsDestDir)) {
        New-Item -ItemType Directory -Force -Path $scriptsDestDir | Out-Null
    }
    Write-Host "[INFO] Copying python helper scripts to installer package..." -ForegroundColor Yellow
    Copy-Item -Path "$scriptsSrcPath\*" -Destination $scriptsDestDir -Force -Recurse
    Write-Host "[OK] Copied python helper scripts to: $scriptsDestDir" -ForegroundColor Green
}

# 4.7 Ensure conpty.dll and OpenConsole.exe are copied to node-pty build folder
$conptyDestDir = Join-Path $vsCodePackDir "resources\app\node_modules\node-pty\build\Release\conpty"
if (-not (Test-Path $conptyDestDir)) {
    New-Item -ItemType Directory -Force -Path $conptyDestDir | Out-Null
}
$conptySrcFolder = Join-Path (Split-Path $PSScriptRoot -Parent) "IDE\vscode\node_modules\node-pty\third_party\conpty\1.25.260303002\win10-x64"
if (Test-Path $conptySrcFolder) {
    Write-Host "[INFO] Copying conpty binaries to packaged node-pty folder..." -ForegroundColor Yellow
    Copy-Item -Path "$conptySrcFolder\*" -Destination $conptyDestDir -Force
    Write-Host "[OK] Copied conpty binaries to: $conptyDestDir" -ForegroundColor Green
}

# 4.85 Apply native module stubs (no prebuilt .node binaries shipped with build)
# These stubs replace @vscode/policy-watcher, @vscode/spdlog, @vscode/windows-mutex
# with no-op JS implementations so the IDE starts without native Electron bindings.
$stubsDir = Join-Path $PSScriptRoot "patches\native_stubs"
if (Test-Path $stubsDir) {
    $stubMap = @{
        "@vscode_policy-watcher_index.js" = "resources\app\node_modules\@vscode\policy-watcher\index.js"
        "@vscode_spdlog_index.js"         = "resources\app\node_modules\@vscode\spdlog\index.js"
        "@vscode_windows-mutex_index.js"  = "resources\app\node_modules\@vscode\windows-mutex\index.js"
    }
    foreach ($stub in $stubMap.GetEnumerator()) {
        $stubSrc = Join-Path $stubsDir $stub.Key
        $stubDst = Join-Path $vsCodePackDir $stub.Value
        if ((Test-Path $stubSrc) -and (Test-Path (Split-Path $stubDst -Parent))) {
            Copy-Item $stubSrc $stubDst -Force
            Write-Host "[OK] Applied native stub: $($stub.Value)" -ForegroundColor Green
        }
    }
} else {
    Write-Host "[WARNING] Native stubs directory not found at $stubsDir - IDE may fail to start." -ForegroundColor Yellow
}

# 4.8 Bundle starter OpenVINO model for offline-ready experience
$ovModelName = "OpenVINO--Qwen2.5-1.5B-Instruct-int4-ov"
$ovSrcPath = Join-Path $env:USERPROFILE ".hugos-ide\ov_models\$ovModelName"
if (Test-Path $ovSrcPath) {
    $ovDestDir = Join-Path $vsCodePackDir "ov_models\$ovModelName"
    if (-not (Test-Path $ovDestDir)) {
        New-Item -ItemType Directory -Force -Path $ovDestDir | Out-Null
    }
    Write-Host "[INFO] Bundling starter OpenVINO model ($ovModelName) into installer..." -ForegroundColor Yellow
    # Copy only the essential model files (skip .metadata and cache files)
    Get-ChildItem -Path $ovSrcPath -File | Where-Object { $_.Name -notlike "*.metadata" -and $_.Name -ne "CACHEDIR.TAG" -and $_.Name -ne ".gitignore" } | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $ovDestDir -Force
    }
    $modelSize = [math]::Round((Get-ChildItem $ovDestDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    Write-Host "[OK] Bundled starter model ($modelSize MB) to: $ovDestDir" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Starter OpenVINO model not found at $ovSrcPath. Packaging without bundled model." -ForegroundColor Yellow
}

# 5. Sign the binaries
Write-Host "[INFO] Signing executables, DLLs, and native modules inside packaged folder..." -ForegroundColor Yellow
# IMPORTANT: Do NOT sign Electron binaries or GPU/DirectX DLLs.
# - HugOS.exe uses Code.exe from VSCode which has a valid Microsoft signature — do not overwrite it.
# - GPU/DirectX DLLs must keep their original signatures or Electron's renderer won't start.
$dllExcludeList = @(
    'HugOS.exe',          # Main Electron binary — uses Microsoft-signed Code.exe
    'dxil.dll',           # DirectX IL runtime — requires Microsoft signature
    'd3dcompiler_47.dll', # DirectX compiler — validated by Windows
    'dxcompiler.dll',     # DX compiler runtime
    'vk_swiftshader.dll', # Vulkan SwiftShader — Khronos/Google signed
    'libEGL.dll',         # ANGLE EGL — Google signed
    'libGLESv2.dll',      # ANGLE GLES2 — Google signed
    'ffmpeg.dll'          # FFmpeg — Chromium signed
)
$filesToSign = Get-ChildItem -Path $vsCodePackDir -Include *.exe, *.dll, *.node -Recurse |
    Where-Object { $dllExcludeList -notcontains $_.Name } |
    Select-Object -ExpandProperty FullName


$count = 0
foreach ($file in $filesToSign) {
    # Skip files that are already signed or fail to sign (like some readonly or system files)
    # We will attempt to sign with a retry in case of transient timestamp issues
    Write-Host "Signing: $file"
    $signed = $false
    for ($i = 0; $i -lt 2; $i++) {
        # Try signing with timestamp
        & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $file 2>$null
        if ($LASTEXITCODE -eq 0) {
            $signed = $true
            break
        }
        # Try signing without timestamp as fallback
        & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 $file 2>$null
        if ($LASTEXITCODE -eq 0) {
            $signed = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if ($signed) { $count++ }
}
Write-Host "[OK] Signed $count files inside the packaging directory." -ForegroundColor Green

# 6. Generate the WiX source manifest (.wxs)
Write-Host "[INFO] Generating WiX source manifest (.wxs)..." -ForegroundColor Yellow
$wxsPath = Join-Path $PSScriptRoot "HugOS.wxs"
node (Join-Path $PSScriptRoot "generate_wix.js") $vsCodePackDir $wxsPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to run generate_wix.js." -ForegroundColor Red
    Exit 1
}
Write-Host "[OK] WiX source generated at $wxsPath" -ForegroundColor Green

# 7. Compile the MSI using WiX Toolset v7
Write-Host "[INFO] Compiling MSI using WiX Toolset v7..." -ForegroundColor Yellow
$msiPath = Join-Path $PSScriptRoot "HugOS.msi"
if (Test-Path $msiPath) {
    Remove-Item -Path $msiPath -Force
}

# Run wix build
& wix build -arch x64 $wxsPath -out $msiPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] WiX build failed." -ForegroundColor Red
    Exit 1
}
Write-Host "[OK] MSI built successfully at $msiPath" -ForegroundColor Green

# 8. Sign the final MSI file
Write-Host "[INFO] Signing final MSI package..." -ForegroundColor Yellow
$signedMsi = $false
for ($i = 0; $i -lt 3; $i++) {
    & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $msiPath
    if ($LASTEXITCODE -eq 0) {
        $signedMsi = $true
        break
    }
    & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 $msiPath
    if ($LASTEXITCODE -eq 0) {
        $signedMsi = $true
        break
    }
    Start-Sleep -Seconds 2
}

if ($signedMsi) {
    Write-Host "[OK] Signed final MSI installer successfully!" -ForegroundColor Green
    Write-Host "[INFO] Verifying signature (warnings/errors are expected for self-signed certificates)..." -ForegroundColor Yellow
    & $signtoolPath verify /pa $msiPath 2>&1 | Out-String | Write-Host
    Write-Host "[SUCCESS] Process complete. MSI installer generated at: $msiPath" -ForegroundColor Green
    Exit 0
} else {
    Write-Host "[ERROR] Failed to sign final MSI installer." -ForegroundColor Red
    Exit 1
}
