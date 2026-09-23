# HugOS IDE Signed MSI Packaging Script
# This script compiles, copies cli.exe, signs all binaries, generates a WiX manifest, and builds/signs the final MSI.

$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$vsCodePackDir = Join-Path (Split-Path $PSScriptRoot -Parent) "IDE\VSCode-win32-x64"
$pfxPath = Join-Path $PSScriptRoot "hugos-signing-cert.pfx"
$password = "HugOSPassword123!"

# Ensure common tools are available in PATH
$toolDirs = @(
    "D:\tools\nodejs",
    "D:\tools\wix\PFiles64\WiX Toolset v5.0\bin",
    "D:\tools\gh\bin",
    "C:\Program Files\dotnet",
    "C:\Users\oyesanyf\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.MSVCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin"
)
foreach ($td in $toolDirs) {
    if ((Test-Path $td) -and ($env:PATH -notlike "*$td*")) {
        $env:PATH = "$td;" + $env:PATH
    }
}

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

# 2. Locate signtool.exe or setup PowerShell Set-AuthenticodeSignature
$signtoolPath = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
if (-not (Test-Path $signtoolPath)) {
    Write-Host "[INFO] Signtool not found at default path, searching Windows Kits..." -ForegroundColor Yellow
    $signtoolPath = Get-ChildItem -Path 'C:\Program Files (x86)\Windows Kits', 'C:\Program Files\Windows Kits', 'D:\tools' -Filter signtool.exe -Recurse -Depth 4 -ErrorAction SilentlyContinue | 
                    Where-Object { $_.FullName -like "*x64*" } | 
                    Select-Object -ExpandProperty FullName -First 1
}

if ($signtoolPath) {
    Write-Host "[OK] Using signtool at: $signtoolPath" -ForegroundColor Green
} else {
    Write-Host "[INFO] signtool.exe not found. Using native PowerShell Set-AuthenticodeSignature." -ForegroundColor Yellow
}

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

$pwdSecure = ConvertTo-SecureString $password -AsPlainText -Force
$signCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($pfxPath, $pwdSecure)

function Sign-FileWithCert {
    param([string]$FilePath)
    if ($signtoolPath) {
        for ($i = 0; $i -lt 2; $i++) {
            & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $FilePath 2>$null
            if ($LASTEXITCODE -eq 0) { return $true }
            & $signtoolPath sign /f $pfxPath /p $password /fd SHA256 $FilePath 2>$null
            if ($LASTEXITCODE -eq 0) { return $true }
            Start-Sleep -Seconds 1
        }
        return $false
    } else {
        for ($i = 0; $i -lt 2; $i++) {
            try {
                $res = Set-AuthenticodeSignature -FilePath $FilePath -Certificate $signCert -TimestampServer "http://timestamp.digicert.com" -HashAlgorithm SHA256 -ErrorAction SilentlyContinue
                if ($res -and $res.SignerCertificate) { return $true }
            } catch {}
            try {
                $res = Set-AuthenticodeSignature -FilePath $FilePath -Certificate $signCert -HashAlgorithm SHA256 -ErrorAction SilentlyContinue
                if ($res -and $res.SignerCertificate) { return $true }
            } catch {}
            Start-Sleep -Seconds 1
        }
        return $false
    }
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

# Check if current HugOS.exe has a valid (Microsoft) signature AND the versioned runtime dir exists
$exeSig = Get-AuthenticodeSignature $hugosExePath -ErrorAction SilentlyContinue
$versionedDirExists = (Get-ChildItem $vsCodePackDir -Directory | Where-Object { $_.Name -match '^[0-9a-f]{7,40}$' }).Count -gt 0
if ($exeSig.Status -ne 'Valid' -or $exeSig.SignerCertificate.Subject -notlike '*Microsoft*' -or -not $versionedDirExists) {
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
    $versionedDir = Get-ChildItem $extractDir -Directory | Where-Object { $_.Name -match '^[0-9a-f]{7,40}$' } | Select-Object -First 1
    if ($versionedDir) {
        $destVersionedDir = Join-Path $vsCodePackDir $versionedDir.Name
        Copy-Item $versionedDir.FullName $destVersionedDir -Recurse -Force
        Write-Host "[OK] Copied Electron versioned runtime directory: $($versionedDir.Name)/" -ForegroundColor Green

        # CRITICAL: Replace the versioned dir's product.json with HugOS branding.
        # The VSCode zip ships with product.json containing nameShort:"Code" / nameLong:"Visual Studio Code"
        # which OVERRIDES our resources/app/product.json and makes the IDE show VSCode branding.
        $versionedProductJson = Join-Path $destVersionedDir "resources\app\product.json"
        $authoritativePj = Join-Path $PSScriptRoot "patches\product.json"
        if (Test-Path $authoritativePj) {
            $vPjDir = Split-Path $versionedProductJson -Parent
            if (-not (Test-Path $vPjDir)) {
                New-Item -ItemType Directory -Force -Path $vPjDir | Out-Null
            }
            Copy-Item $authoritativePj $versionedProductJson -Force -ErrorAction Stop
            Write-Host "[OK] Replaced versioned product.json with authoritative HugOS product.json" -ForegroundColor Green
        }

        # CRITICAL: Copy our custom Copilot/ModelFusion extension into the versioned directory,
        # REPLACING the stock GitHub Copilot extension. Our custom extension has ModelFusion
        # settings, OpenEvolve, /security, and other HugOS-specific features.
        # The extension may be named 'copilot' (pre-rename) or 'modelfusion' (post-rename).
        $copilotExtSrc = Join-Path $vsCodePackDir "resources\app\extensions\copilot"
        $mfExtSrc = Join-Path $vsCodePackDir "resources\app\extensions\modelfusion"
        if (Test-Path $copilotExtSrc) {
            $destCopilot = Join-Path $destVersionedDir "resources\app\extensions\copilot"
            Remove-Item $destCopilot -Recurse -Force -ErrorAction SilentlyContinue
            Copy-Item $copilotExtSrc $destCopilot -Recurse -Force
            Write-Host "[OK] Replaced stock copilot extension with HugOS custom copilot extension" -ForegroundColor Green
        } elseif (Test-Path $mfExtSrc) {
            $destMF = Join-Path $destVersionedDir "resources\app\extensions\modelfusion"
            Copy-Item $mfExtSrc $destMF -Recurse -Force
            Write-Host "[OK] Copied modelfusion extension to versioned directory" -ForegroundColor Green
        } else {
            Write-Host "[WARNING] Neither copilot nor modelfusion extension found in source build!" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[WARNING] No versioned runtime directory found in VSCode zip!" -ForegroundColor Yellow
    }

    Write-Host "[OK] Electron runtime data files synced" -ForegroundColor Green
    Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "[OK] HugOS.exe already has valid Microsoft signature - no restore needed" -ForegroundColor Green
}

# 4.2 Unconditionally deploy authoritative product.json from IDE/patches/product.json
# The patched product.json at IDE/patches/product.json is the authoritative source
# for HugOS branding, defaultChatAgent (GitHub.copilot-chat), extensionEnabledApiProposals, etc.
# This MUST be copied to both resources/app/product.json AND all versioned runtime directories
# unconditionally (whether or not Step 4.1 performed an Electron binary restore).
Write-Host "[INFO] Deploying authoritative product.json to packaged directory..." -ForegroundColor Yellow
$authoritativeProductJson = Join-Path $PSScriptRoot "patches\product.json"
if (-not (Test-Path $authoritativeProductJson)) {
    Write-Host "[ERROR] Authoritative product.json not found at: $authoritativeProductJson" -ForegroundColor Red
    Exit 1
}

# 1. Copy to root resources/app/product.json
$rootProductJson = Join-Path $vsCodePackDir "resources\app\product.json"
$rootPjDir = Split-Path $rootProductJson -Parent
if (-not (Test-Path $rootPjDir)) {
    New-Item -ItemType Directory -Force -Path $rootPjDir | Out-Null
}
Copy-Item -Path $authoritativeProductJson -Destination $rootProductJson -Force -ErrorAction Stop
Write-Host "[OK] Deployed authoritative product.json to: $rootProductJson" -ForegroundColor Green

# 2. Copy to all versioned runtime directories (e.g., 7e7950df89/resources/app/product.json)
$versionedDirs = @(Get-ChildItem $vsCodePackDir -Directory | Where-Object { $_.Name -match '^[0-9a-f]{7,40}$' })
if ($versionedDirs.Count -eq 0) {
    Write-Host "[WARNING] No versioned runtime directories found in $vsCodePackDir!" -ForegroundColor Yellow
}
foreach ($vDir in $versionedDirs) {
    $vProductJson = Join-Path $vDir.FullName "resources\app\product.json"
    $vProductJsonDir = Split-Path $vProductJson -Parent
    if (-not (Test-Path $vProductJsonDir)) {
        New-Item -ItemType Directory -Force -Path $vProductJsonDir | Out-Null
    }
    Copy-Item -Path $authoritativeProductJson -Destination $vProductJson -Force -ErrorAction Stop
    Write-Host "[OK] Deployed authoritative product.json to versioned dir: $vProductJson" -ForegroundColor Green

    # CRITICAL: Deploy authoritative NLS localization tables to versioned dir
    # to guarantee exact 1:1 index alignment with workbench.desktop.main.js
    foreach ($nlsFile in @('nls.messages.js', 'nls.messages.json', 'nls.metadata.json', 'nls.keys.json')) {
        $rootNls = Join-Path $vsCodePackDir "resources\app\out\$nlsFile"
        $vNls = Join-Path $vDir.FullName "resources\app\out\$nlsFile"
        if (Test-Path $rootNls) {
            $vNlsDir = Split-Path $vNls -Parent
            if (-not (Test-Path $vNlsDir)) { New-Item -ItemType Directory -Force -Path $vNlsDir | Out-Null }
            Copy-Item -Path $rootNls -Destination $vNls -Force -ErrorAction Stop
            Write-Host "[OK] Deployed authoritative $nlsFile to versioned dir: $vNls" -ForegroundColor Green
        }
    }
}

# 4.5 Copy Pre-populated HF Models Database (hf_models.db) into the packaged folder
$candidateDbs = @(
    (Join-Path $PSScriptRoot "db\hf_models.db"),
    (Join-Path (Split-Path $PSScriptRoot -Parent) "db\hf_models.db")
)
$dbSrcPath = $candidateDbs | Where-Object { (Test-Path $_) -and (Get-Item $_).Length -gt 50000 } | Select-Object -First 1
if (-not $dbSrcPath) {
    $dbSrcPath = Join-Path (Split-Path $PSScriptRoot -Parent) "db\hf_models.db"
}
if (Test-Path $dbSrcPath) {
    $dbDestDir = Join-Path $vsCodePackDir "db"
    if (-not (Test-Path $dbDestDir)) {
        New-Item -ItemType Directory -Force -Path $dbDestDir | Out-Null
    }
    $dbDestPath = Join-Path $dbDestDir "hf_models.db"
    Write-Host "[INFO] Copying pre-populated models database to installer package ($dbSrcPath)..." -ForegroundColor Yellow
    Copy-Item -Path $dbSrcPath -Destination $dbDestPath -Force
    Write-Host "[OK] Copied ModelFusion Database to: $dbDestPath ($( (Get-Item $dbDestPath).Length ) bytes)" -ForegroundColor Green
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

# 4.65 Copy ReST-RL subsystem and config into packaged folders (root and all versioned runtimes)
$restRlSrc = Join-Path $PSScriptRoot "rest_rl"
if (Test-Path $restRlSrc) {
    Write-Host "[INFO] Copying ReST-RL subsystem into packaged distributions..." -ForegroundColor Yellow
    $restRlTargets = @(
        Join-Path $vsCodePackDir "resources\app\rest_rl"
    )
    $verDirsForRl = Get-ChildItem $vsCodePackDir -Directory | Where-Object { $_.Name -match '^[0-9a-f]{7,40}$' }
    foreach ($vd in $verDirsForRl) {
        $restRlTargets += (Join-Path $vd.FullName "resources\app\rest_rl")
    }

    foreach ($rlDst in $restRlTargets) {
        if (-not (Test-Path $rlDst)) {
            New-Item -ItemType Directory -Force -Path $rlDst | Out-Null
        }
        Copy-Item -Path "$restRlSrc\*" -Destination $rlDst -Recurse -Force
        # Clean temporary Python cache artifacts
        @('__pycache__', '.pytest_cache') | ForEach-Object {
            $unwanted = Join-Path $rlDst $_
            if (Test-Path $unwanted) {
                Remove-Item $unwanted -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
        Get-ChildItem -Path $rlDst -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Get-ChildItem -Path $rlDst -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue

        # Verification assertion gate checking that config.json and daemon exist
        if (-not (Test-Path (Join-Path $rlDst "config.json"))) {
            Write-Error "[ASSERTION FAILED] ReST-RL config.json missing after packaging: $rlDst\config.json"
            exit 1
        }
        if (-not (Test-Path (Join-Path $rlDst "rest_rl_daemon.py"))) {
            Write-Error "[ASSERTION FAILED] ReST-RL daemon missing after packaging: $rlDst\rest_rl_daemon.py"
            exit 1
        }
        Write-Host "[OK] Synced and verified ReST-RL subsystem to: $rlDst" -ForegroundColor Green
    }
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

# 4.9 Patch extensionHostProcess.js to accept ModelFusion as default vendor
# VS Code's getDefaultLanguageModel() hardcodes vendor === "copilot" which blocks our
# "modelfusion" vendor from being found as the default. This patch removes that vendor
# check so any model with isDefaultForLocation.panel = true becomes the default model.
Write-Host "[INFO] Patching extensionHostProcess.js to accept ModelFusion vendor..." -ForegroundColor Yellow
$ejsPatterns = Get-ChildItem -Path $vsCodePackDir -Filter "extensionHostProcess.js" -Recurse
foreach ($ejsFile in $ejsPatterns) {
    $ejsContent = Get-Content $ejsFile.FullName -Raw
    $vendorCheckOld = 'r.metadata.isDefaultForLocation.panel&&r.metadata.vendor===Yl'
    $vendorCheckNew = 'r.metadata.isDefaultForLocation.panel'
    if ($ejsContent.Contains($vendorCheckOld)) {
        $ejsContent = $ejsContent.Replace($vendorCheckOld, $vendorCheckNew)
        Set-Content $ejsFile.FullName -Value $ejsContent -NoNewline
        Write-Host "[OK] Patched vendor check in: $($ejsFile.FullName)" -ForegroundColor Green
    } else {
        Write-Host "[SKIP] Vendor check already patched or not found in: $($ejsFile.FullName)" -ForegroundColor Yellow
    }
}

# 4.95 Strip checksums from product.json to prevent "corrupt installation" warning
# When product.json contains a checksums block, VS Code validates file hashes at startup.
# Our patches naturally change file hashes, so we remove the block to avoid false alarms.
Write-Host "[INFO] Stripping checksums from product.json..." -ForegroundColor Yellow
$productJsonFiles = Get-ChildItem -Path $vsCodePackDir -Filter "product.json" -Recurse |
    Where-Object { $_.FullName -like "*resources\app\product.json" }
foreach ($pjFile in $productJsonFiles) {
    $pjObj = Get-Content $pjFile.FullName -Raw | ConvertFrom-Json
    if ($pjObj.checksums) {
        $pjObj.PSObject.Properties.Remove('checksums')
        [System.IO.File]::WriteAllText($pjFile.FullName, ($pjObj | ConvertTo-Json -Depth 20), (New-Object System.Text.UTF8Encoding($false)))
        Write-Host "[OK] Removed checksums from: $($pjFile.FullName)" -ForegroundColor Green
    }
}

# 4.96 Disable GitHub login prompts - HugOS uses local ModelFusion, not GitHub Copilot auth
Write-Host "[INFO] Disabling GitHub login prompts..." -ForegroundColor Yellow
foreach ($pjFile in $productJsonFiles) {
    $pjObj = Get-Content $pjFile.FullName -Raw | ConvertFrom-Json
    $changed = $false

    # Remove the GitHub auth provider requirement from defaultChatAgent
    if ($pjObj.defaultChatAgent -and ($pjObj.defaultChatAgent.providerExtensionId -or $pjObj.defaultChatAgent.signUpUrl -or $pjObj.defaultChatAgent.entitlementUrl)) {
        $pjObj.defaultChatAgent.providerExtensionId = ""
        $pjObj.defaultChatAgent.entitlementUrl = ""
        $pjObj.defaultChatAgent.entitlementSignupLimitedUrl = ""
        $pjObj.defaultChatAgent.tokenEntitlementUrl = ""
        $pjObj.defaultChatAgent.signUpUrl = ""
        $changed = $true
    }

    if ($changed) {
        # Retain trustedExtensionAuthAccess from authoritative product.json (required for copilot-chat)
        [System.IO.File]::WriteAllText($pjFile.FullName, ($pjObj | ConvertTo-Json -Depth 20), (New-Object System.Text.UTF8Encoding($false)))
        Write-Host "[OK] Disabled GitHub auth in: $($pjFile.FullName)" -ForegroundColor Green
    } else {
        Write-Host "[INFO] GitHub auth already disabled in: $($pjFile.FullName)" -ForegroundColor Green
    }
}

# Ensure GitHub authentication is optional (no forced popups, but available if desired)
$patchOptGithub = Join-Path $PSScriptRoot "patch_optional_github.py"
if (Test-Path $patchOptGithub) {
    python $patchOptGithub
    Write-Host "[OK] Configured optional GitHub authentication (popups suppressed, login available)" -ForegroundColor Green
}

# Inject default settings to suppress any remaining auth/login prompts
$defaultSettingsDir = Join-Path $vsCodePackDir "resources\app\out\vs\platform\configuration\common"
if (-not (Test-Path $defaultSettingsDir)) {
    $defaultSettingsDir = Join-Path $vsCodePackDir "resources\app"
}
$machineSettingsPath = Join-Path $vsCodePackDir "resources\app\product-default-settings.json"
$defaultSettings = @{
    "chat.agent.enabled" = $true
    "chat.utilityModel" = "modelfusion/modelfusion-local"
    "chat.utilitySmallModel" = "modelfusion/modelfusion-local"
    "hugos.modelfusion.fusion" = $true
    "hugos.modelfusion.fusionModels" = 0
    "github.copilot.enable" = @{ "*" = $false }
    "github.gitAuthentication" = $false
    "git.autofetch" = $false
    "workbench.accounts.experimental.showEntitlements" = $false
    "workbench.enableExperiments" = $false
    "telemetry.telemetryLevel" = "off"
    "update.mode" = "none"
    "update.enableWindowsBackgroundUpdates" = $false
    "update.showReleaseNotes" = $false
    "extensions.autoCheckUpdates" = $false
    "extensions.autoUpdate" = $false
}
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($machineSettingsPath, ($defaultSettings | ConvertTo-Json -Depth 10), $utf8NoBom)
Write-Host "[OK] Injected default settings to suppress login prompts: $machineSettingsPath" -ForegroundColor Green

# Also deploy product-default-settings.json to all versioned runtime directories
$verDirsForPds = Get-ChildItem $vsCodePackDir -Directory | Where-Object { $_.Name -match '^[0-9a-f]{7,40}$' }
foreach ($vd in $verDirsForPds) {
    $vSettingsDir = Join-Path $vd.FullName "resources\app"
    if (Test-Path $vSettingsDir) {
        $vSettingsPath = Join-Path $vSettingsDir "product-default-settings.json"
        [System.IO.File]::WriteAllText($vSettingsPath, ($defaultSettings | ConvertTo-Json -Depth 10), $utf8NoBom)
        Write-Host "[OK] Injected default settings to versioned runtime: $vSettingsPath" -ForegroundColor Green
    }
}

# 4.965 Sync ModelFusion / Copilot extension and AVO framework into packaged distributions
Write-Host "[INFO] Syncing custom copilot extension and AVO into packaged folder..." -ForegroundColor Yellow
$srcExtDir = Join-Path $PSScriptRoot "vscode\extensions\copilot"
$targetExtDirs = @(
    Join-Path $vsCodePackDir "resources\app\extensions\copilot"
)
# Also target versioned runtime directories if present
$verDirs = Get-ChildItem $vsCodePackDir -Directory | Where-Object { $_.Name -match '^[0-9a-f]{7,40}$' }
foreach ($vd in $verDirs) {
    $targetExtDirs += (Join-Path $vd.FullName "resources\app\extensions\copilot")
}

foreach ($tDir in $targetExtDirs) {
    if (-not (Test-Path $tDir)) {
        New-Item -ItemType Directory -Force -Path $tDir | Out-Null
    }
    # Sync dist/
    $distSrc = Join-Path $srcExtDir "dist"
    $distDst = Join-Path $tDir "dist"
    if (Test-Path $distSrc) {
        if (-not (Test-Path $distDst)) { New-Item -ItemType Directory -Force -Path $distDst | Out-Null }
        Copy-Item -Path "$distSrc\*" -Destination $distDst -Recurse -Force
    }
    # Sync package.json
    $pkgSrc = Join-Path $srcExtDir "package.json"
    if (Test-Path $pkgSrc) {
        Copy-Item -Path $pkgSrc -Destination (Join-Path $tDir "package.json") -Force
    }
    # Sync avo/
    $avoSrc = Join-Path $srcExtDir "avo"
    $avoDst = Join-Path $tDir "avo"
    $avoDest = $avoDst
    if (Test-Path $avoSrc) {
        if (-not (Test-Path $avoDst)) { New-Item -ItemType Directory -Force -Path $avoDst | Out-Null }
        Copy-Item -Path "$avoSrc\*" -Destination $avoDst -Recurse -Force

        # Exclude .git, runs, __pycache__, and temporary artifacts from packaging
        @('.git', '.claude', 'runs', '__pycache__', '.pytest_cache', '.venv') | ForEach-Object {
            $unwanted = Join-Path $avoDest $_
            if (Test-Path $unwanted) {
                Remove-Item $unwanted -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
        Get-ChildItem -Path $avoDest -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Get-ChildItem -Path $avoDest -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue

        # Verification assertion gate checking that Test-Path "$avoDest\src\avo\cli.py" passes
        if (-not (Test-Path "$avoDest\src\avo\cli.py")) {
            Write-Error "[ASSERTION FAILED] AVO CLI entrypoint missing after packaging: $avoDest\src\avo\cli.py"
            exit 1
        }
        Write-Host "[OK] Verified AVO CLI entrypoint at: $avoDest\src\avo\cli.py" -ForegroundColor Green
    }
    Write-Host "[OK] Synced extension dist and avo to: $tDir" -ForegroundColor Green
}

# 4.97 Apply ModelFusion extension patches (Slash Commands, @agent routing, OpenEvolve diffs)
Write-Host "[INFO] Applying extension slash command and OpenEvolve patches..." -ForegroundColor Yellow
$registerRlScript = Join-Path $PSScriptRoot "register_rest_rl_commands.py"
if (Test-Path $registerRlScript) {
    python $registerRlScript
    Write-Host "[OK] Registered ReST-RL slash commands in package.json" -ForegroundColor Green
}
$fixSlashScript = Join-Path $PSScriptRoot "fix_slash_commands.py"
if (Test-Path $fixSlashScript) {
    python $fixSlashScript
    Write-Host "[OK] Applied slash command patches" -ForegroundColor Green
}
$patchEvolveScript = Join-Path $PSScriptRoot "patch_evolve_save.py"
if (Test-Path $patchEvolveScript) {
    python $patchEvolveScript
    Write-Host "[OK] Applied OpenEvolve display & save patches" -ForegroundColor Green
}
$patchApplyCodeblockScript = Join-Path $PSScriptRoot "patch_apply_codeblock.py"
if (Test-Path $patchApplyCodeblockScript) {
    python $patchApplyCodeblockScript
    Write-Host "[OK] Applied code block apply and auto-save patches" -ForegroundColor Green
}
$patchFusionScript = Join-Path $PSScriptRoot "patch_evolution_fusion.py"
if (Test-Path $patchFusionScript) {
    python $patchFusionScript
    Write-Host "[OK] Applied evolution multi-model fusion patches" -ForegroundColor Green
}
$patchAvoOutputScript = Join-Path $PSScriptRoot "patch_avo_output.py"
if (Test-Path $patchAvoOutputScript) {
    python $patchAvoOutputScript
    Write-Host "[OK] Applied AVO output reporting & diagnostic patches" -ForegroundColor Green
}
$patchProductJsonScript = Join-Path $PSScriptRoot "patch_product_json.py"
if (Test-Path $patchProductJsonScript) {
    python $patchProductJsonScript "$vsCodePackDir"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] product.json patch script failed! Aborting MSI build." -ForegroundColor Red
        Exit 1
    }
    Write-Host "[OK] Applied product.json alignment and API proposals" -ForegroundColor Green
}

$verifyProductJsonScript = Join-Path $PSScriptRoot "verify_product_json.ps1"
if (Test-Path $verifyProductJsonScript) {
    & powershell -ExecutionPolicy Bypass -File $verifyProductJsonScript -PackDir $vsCodePackDir -CheckInstalled $false
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] product.json verification failed! Aborting MSI build." -ForegroundColor Red
        Exit 1
    }
    Write-Host "[OK] Verified product.json configuration successfully" -ForegroundColor Green
}

# 4.975 Apply workbench.desktop.main.js chat enablement patches
Write-Host "[INFO] Applying workbench chat enablement patches..." -ForegroundColor Yellow
$patchWorkbenchScript = Join-Path $PSScriptRoot "patch_workbench.py"
if (Test-Path $patchWorkbenchScript) {
    python $patchWorkbenchScript "$vsCodePackDir" --skip-installed
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] workbench patch script failed! Aborting MSI build." -ForegroundColor Red
        Exit 1
    }
    Write-Host "[OK] Applied workbench chat enablement patches" -ForegroundColor Green
}

# 4.976 Apply utility model preset & BYOK popup suppression patches
Write-Host "[INFO] Applying utility model preset and BYOK popup suppression patches..." -ForegroundColor Yellow
$patchUtilityScript = Join-Path $PSScriptRoot "patch_utility_models.py"
if (Test-Path $patchUtilityScript) {
    python $patchUtilityScript "$vsCodePackDir" --skip-installed
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] patch_utility_models script failed! Aborting MSI build." -ForegroundColor Red
        Exit 1
    }
    Write-Host "[OK] Applied utility model preset and BYOK popup suppression patches" -ForegroundColor Green
}

# 4.977 Apply Ollama PATH and hardware scaling patches
Write-Host "[INFO] Applying Ollama PATH and hardware scaling patches..." -ForegroundColor Yellow
$patchOllamaScript = Join-Path $PSScriptRoot "patch_ollama_path.py"
if (Test-Path $patchOllamaScript) {
    python $patchOllamaScript "$vsCodePackDir" --skip-installed
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] patch_ollama_path script failed! Aborting MSI build." -ForegroundColor Red
        Exit 1
    }
}

# 4.98 Ensure 100% parity and presence across all versioned runtime directories
Write-Host "[INFO] Synchronizing all configuration, settings, extensions, and ReST-RL to versioned runtime directories..." -ForegroundColor Yellow
$versionedDirs = @(Get-ChildItem $vsCodePackDir -Directory | Where-Object { $_.Name -match '^[0-9a-f]{7,40}$' })
foreach ($vDir in $versionedDirs) {
    $vAppDir = Join-Path $vDir.FullName "resources\app"
    $vCopilotDir = Join-Path $vAppDir "extensions\copilot"
    $vCopilotDistDir = Join-Path $vCopilotDir "dist"
    $vRestRlDir = Join-Path $vAppDir "rest_rl"
    $vOutVsDir = Join-Path $vAppDir "out\vs\workbench"
    
    # Ensure all target parent directories exist
    @($vAppDir, $vCopilotDir, $vCopilotDistDir, $vRestRlDir, $vOutVsDir) | ForEach-Object {
        if (-not (Test-Path $_)) { New-Item -ItemType Directory -Force -Path $_ | Out-Null }
    }
    
    # 1. Authoritative product.json
    $srcPj = Join-Path $vsCodePackDir "resources\app\product.json"
    if (Test-Path $srcPj) {
        Copy-Item -Path $srcPj -Destination (Join-Path $vAppDir "product.json") -Force
    } elseif (Test-Path $authoritativeProductJson) {
        Copy-Item -Path $authoritativeProductJson -Destination (Join-Path $vAppDir "product.json") -Force
    }
    
    # 2. product-default-settings.json
    $srcPds = Join-Path $vsCodePackDir "resources\app\product-default-settings.json"
    if (Test-Path $srcPds) {
        Copy-Item -Path $srcPds -Destination (Join-Path $vAppDir "product-default-settings.json") -Force
    } elseif ($defaultSettings) {
        $pdsPath = Join-Path $vAppDir "product-default-settings.json"
        [System.IO.File]::WriteAllText($pdsPath, ($defaultSettings | ConvertTo-Json -Depth 10), $utf8NoBom)
    }
    
    # 3. Copilot package.json
    $srcPkg = Join-Path $vsCodePackDir "resources\app\extensions\copilot\package.json"
    if (Test-Path $srcPkg) {
        Copy-Item -Path $srcPkg -Destination (Join-Path $vCopilotDir "package.json") -Force
    }
    
    # 4. Copilot dist/extension.js
    $srcExt = Join-Path $vsCodePackDir "resources\app\extensions\copilot\dist\extension.js"
    if (Test-Path $srcExt) {
        Copy-Item -Path $srcExt -Destination (Join-Path $vCopilotDistDir "extension.js") -Force
    }
    
    # 5. Workbench main js
    $srcWb = Join-Path $vsCodePackDir "resources\app\out\vs\workbench\workbench.desktop.main.js"
    if (Test-Path $srcWb) {
        Copy-Item -Path $srcWb -Destination (Join-Path $vOutVsDir "workbench.desktop.main.js") -Force
    }
    
    # 5.1 Main entry point js (electron main process)
    $srcMain = Join-Path $vsCodePackDir "resources\app\out\main.js"
    if (Test-Path $srcMain) {
        $vOutMainDir = Join-Path $vAppDir "out"
        if (-not (Test-Path $vOutMainDir)) { New-Item -ItemType Directory -Path $vOutMainDir -Force | Out-Null }
        Copy-Item -Path $srcMain -Destination (Join-Path $vOutMainDir "main.js") -Force
    }

    # 5.2 Deploy authoritative NLS localization tables
    foreach ($nlsFile in @('nls.messages.js', 'nls.messages.json', 'nls.metadata.json', 'nls.keys.json')) {
        $srcNls = Join-Path $vsCodePackDir "resources\app\out\$nlsFile"
        $dstNls = Join-Path $vAppDir "out\$nlsFile"
        if (Test-Path $srcNls) {
            $vNlsDir = Split-Path $dstNls -Parent
            if (-not (Test-Path $vNlsDir)) { New-Item -ItemType Directory -Force -Path $vNlsDir | Out-Null }
            Copy-Item -Path $srcNls -Destination $dstNls -Force -ErrorAction Stop
            Write-Host "[OK] Deployed authoritative $nlsFile to versioned dir: $dstNls" -ForegroundColor Green
        }
    }
    
    # 6. ReST-RL subsystem
    $srcRestRl = Join-Path $vsCodePackDir "resources\app\rest_rl"
    if (Test-Path $srcRestRl) {
        Copy-Item -Path "$srcRestRl\*" -Destination $vRestRlDir -Recurse -Force
    }
    Write-Host "[OK] Fully synchronized versioned runtime directory: $($vDir.Name)" -ForegroundColor Green
}

# 4.99 Validate NLS index alignment across all packaging directories
Write-Host "[INFO] Validating NLS localization indices across all packaging directories..." -ForegroundColor Yellow
$nlsCheckPy = "
import sys, os, json
pack_dir = sys.argv[1]
expected = {5440:'&&Edit', 5441:'&&File', 5442:'&&Go', 5443:'&&Help', 5444:'&&Preferences', 5445:'&&Selection', 5446:'&&Terminal', 5447:'&&View', 5448:'Check for &&Updates...', 5449:'Checking for Updates...', 5450:'D&&ownload Update', 5451:'Downloading Update...', 5453:'Open Settings', 11486:'&&Run', 12864:'Explorer'}
dirs = [os.path.join(pack_dir, 'resources', 'app', 'out')]
for e in os.listdir(pack_dir):
    v = os.path.join(pack_dir, e, 'resources', 'app', 'out')
    if os.path.isdir(v): dirs.append(v)

for d in dirs:
    jp = os.path.join(d, 'nls.messages.json')
    if not os.path.isfile(jp):
        print(f'MISSING: {jp}', file=sys.stderr); sys.exit(1)
    with open(jp, 'r', encoding='utf-8') as f: arr = json.load(f)
    for idx, exp in expected.items():
        val = arr[idx] if idx < len(arr) else 'EOF'
        if val != exp:
            print(f'MISMATCH in {jp} at {idx}: expected {exp}, got {val}', file=sys.stderr)
            sys.exit(1)
print(f'Validated NLS indices across {len(dirs)} packaging directories: 100% aligned.')
"
python -c "$nlsCheckPy" "$vsCodePackDir"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] NLS index alignment verification failed! Aborting MSI build." -ForegroundColor Red
    Exit 1
}
Write-Host "[OK] NLS index alignment verified successfully" -ForegroundColor Green



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
    Where-Object {
        $dllExcludeList -notcontains $_.Name -and
        $_.FullName -notmatch 'darwin' -and
        $_.FullName -notmatch 'linux' -and
        $_.FullName -notmatch 'alpine'
    } |
    Select-Object -ExpandProperty FullName


$count = 0
foreach ($file in $filesToSign) {
    # Skip files that are already signed or fail to sign (like some readonly or system files)
    Write-Host "Signing: $file"
    if (Sign-FileWithCert $file) {
        $count++
    }
}
Write-Host "[OK] Signed $count files inside the packaging directory." -ForegroundColor Green

# Force garbage collection and allow file system handles to settle
[System.GC]::Collect()
[System.GC]::WaitForPendingFinalizers()
Start-Sleep -Seconds 3

# 6. Generate the WiX source manifest (.wxs)
Write-Host "[INFO] Generating WiX source manifest (.wxs)..." -ForegroundColor Yellow
$wxsPath = Join-Path $PSScriptRoot "HugOS.wxs"
$nodeExe = "D:\tools\nodejs\node.exe"
if (-not (Test-Path $nodeExe)) {
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    $nodeExe = if ($nodeCmd) { $nodeCmd.Source } else { "node" }
}
& $nodeExe (Join-Path $PSScriptRoot "generate_wix.js") $vsCodePackDir $wxsPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to run generate_wix.js." -ForegroundColor Red
    Exit 1
}
Write-Host "[OK] WiX source generated at $wxsPath" -ForegroundColor Green

# 7. Compile the MSI using WiX Toolset
Write-Host "[INFO] Compiling MSI using WiX Toolset..." -ForegroundColor Yellow
$msiPath = Join-Path $PSScriptRoot "HugOS.msi"
if (Test-Path $msiPath) {
    Remove-Item -Path $msiPath -Force
}

# Allow file handles to settle before WiX packaging
[System.GC]::Collect()
[System.GC]::WaitForPendingFinalizers()
Start-Sleep -Seconds 3

# Kill any lingering wix or wixnative processes from previous runs
Stop-Process -Name wix, wixnative -Force -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\Temp\#cab*" -Force -Recurse -ErrorAction SilentlyContinue
Remove-Item "$env:TEMP\#cab*" -Force -Recurse -ErrorAction SilentlyContinue

# Run wix build with multi-threaded cabinet compression and bind path
& wix build -b $PSScriptRoot -arch x64 -ct 4 $wxsPath -out $msiPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] WiX build failed." -ForegroundColor Red
    Exit 1
}
Write-Host "[OK] MSI built successfully at $msiPath" -ForegroundColor Green

# 8. Sign the final MSI file
Write-Host "[INFO] Signing final MSI package..." -ForegroundColor Yellow
$signedMsi = Sign-FileWithCert $msiPath

if ($signedMsi) {
    Write-Host "[OK] Signed final MSI installer successfully!" -ForegroundColor Green
    Write-Host "[INFO] Verifying signature (warnings/errors are expected for self-signed certificates)..." -ForegroundColor Yellow
    if ($signtoolPath) {
        & $signtoolPath verify /pa $msiPath 2>&1 | Out-String | Write-Host
    } else {
        Get-AuthenticodeSignature $msiPath | Out-String | Write-Host
    }
    # 9. Verify MSI Package Payload Integrity
    Write-Host "[INFO] Verifying MSI payload contents and configuration presets..." -ForegroundColor Yellow
    $verifyMsiScript = Join-Path $PSScriptRoot "verify_msi_contents.py"
    if (Test-Path $verifyMsiScript) {
        python $verifyMsiScript "$msiPath"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] MSI payload verification failed! Aborting build." -ForegroundColor Red
            Exit 1
        }
        Write-Host "[OK] MSI payload verified 100% compliant and intact" -ForegroundColor Green
    }

    Write-Host "[SUCCESS] Process complete. MSI installer generated at: $msiPath" -ForegroundColor Green
    Exit 0
} else {
    Write-Host "[ERROR] Failed to sign final MSI installer." -ForegroundColor Red
    Exit 1
}
