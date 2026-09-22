# verify_product_json.ps1
# Comprehensive verification suite for HugOS IDE product.json configuration.
#
# Validates:
#   (a) defaultChatAgent.extensionId, chatExtensionId, and chatExtensionOutputId match actual extension ID from package.json
#   (b) extensionEnabledApiProposals contains required proposals (defaultChatParticipant, chatParticipantAdditions)
#   (c) HugOS branding fields are present and valid (nameShort, nameLong, applicationName, win32DirName, etc.)
#   (d) Files are clean BOM-free UTF-8 (preventing Node.js JSON.parse runtime crashes)
#   (e) Required product.json files exist in both root and versioned packaging directories
#
# Exits with return code 0 on success, return code 1 if any check fails.

[CmdletBinding()]
param(
    [string]$PackDir = "",
    $CheckInstalled = $true,
    $RequireVersionedDir = $true
)

$ErrorActionPreference = "Stop"
$failureCount = 0

function Convert-ToBool($val, [bool]$default = $true) {
    if ($null -eq $val) { return $default }
    if ($val -is [bool]) { return $val }
    $s = "$val".Trim().TrimStart('$').ToLower()
    if ($s -in @("true", "1", "yes", "y")) { return $true }
    if ($s -in @("false", "0", "no", "n")) { return $false }
    return $default
}

$shouldCheckInstalled = Convert-ToBool $CheckInstalled $true
$mustRequireVersioned = Convert-ToBool $RequireVersionedDir $true

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
if ([string]::IsNullOrWhiteSpace($PackDir)) {
    $PackDir = Join-Path $scriptDir "VSCode-win32-x64"
} else {
    $PackDir = $PackDir.Trim().Trim('"').Trim("'")
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[VERIFY] HugOS IDE product.json Verification Suite" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Resolve Packaged Directory
if (-not (Test-Path $PackDir)) {
    Write-Host "[FAIL] Packaged directory not found at: $PackDir" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Target packaging directory: $PackDir" -ForegroundColor Green

# 2. Dynamically locate extension package.json to determine actual publisher and name
$copilotPkgCandidates = @(
    (Join-Path $scriptDir "vscode\extensions\copilot\package.json"),
    (Join-Path $PackDir "resources\app\extensions\copilot\package.json"),
    (Join-Path $PackDir "resources\app\extensions\copilot-chat\package.json"),
    (Join-Path $PackDir "resources\app\extensions\modelfusion\package.json")
)

# Dynamically discover versioned runtime directories under PackDir (e.g. 7e7950df89/)
$packVersionedDirs = @(Get-ChildItem $PackDir -Directory | Where-Object { $_.Name -match '^[0-9a-f]{7,40}$' })
foreach ($vd in $packVersionedDirs) {
    $copilotPkgCandidates += (Join-Path $vd.FullName "resources\app\extensions\copilot\package.json")
    $copilotPkgCandidates += (Join-Path $vd.FullName "resources\app\extensions\copilot-chat\package.json")
    $copilotPkgCandidates += (Join-Path $vd.FullName "resources\app\extensions\modelfusion\package.json")
}

# Dynamically discover installed directories in LOCALAPPDATA
if ($shouldCheckInstalled -and $env:LOCALAPPDATA) {
    $installedBase = Join-Path $env:LOCALAPPDATA "HugOS IDE"
    $copilotPkgCandidates += (Join-Path $installedBase "resources\app\extensions\copilot\package.json")
    $copilotPkgCandidates += (Join-Path $installedBase "resources\app\extensions\copilot-chat\package.json")
    $copilotPkgCandidates += (Join-Path $installedBase "resources\app\extensions\modelfusion\package.json")
    if (Test-Path $installedBase) {
        $instVersionedDirs = @(Get-ChildItem $installedBase -Directory | Where-Object { $_.Name -match '^[0-9a-f]{7,40}$' })
        foreach ($ivd in $instVersionedDirs) {
            $copilotPkgCandidates += (Join-Path $ivd.FullName "resources\app\extensions\copilot\package.json")
            $copilotPkgCandidates += (Join-Path $ivd.FullName "resources\app\extensions\copilot-chat\package.json")
            $copilotPkgCandidates += (Join-Path $ivd.FullName "resources\app\extensions\modelfusion\package.json")
        }
    }
}

$pkgJsonPath = $null
foreach ($cand in $copilotPkgCandidates) {
    if (Test-Path $cand) {
        $pkgJsonPath = $cand
        break
    }
}

if (-not $pkgJsonPath) {
    Write-Host "[FAIL] Unable to locate extension package.json in any expected candidate path!" -ForegroundColor Red
    exit 1
}

try {
    $pkgData = Get-Content $pkgJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $extPublisher = "$($pkgData.publisher)".Trim()
    $extName = "$($pkgData.name)".Trim()
    $expectedExtensionId = "$extPublisher.$extName"
    Write-Host "[OK] Located extension package at: $pkgJsonPath" -ForegroundColor Green
    Write-Host "[INFO] Determined actual Extension ID: '$expectedExtensionId' (publisher='$extPublisher', name='$extName')" -ForegroundColor Cyan
} catch {
    Write-Host "[FAIL] Failed to read or parse extension package.json at $pkgJsonPath`: $_" -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($expectedExtensionId)) {
    Write-Host "[FAIL] Extension ID resolved to empty string from $pkgJsonPath!" -ForegroundColor Red
    exit 1
}

# 3. Collect and assert existence of product.json files to validate
$targetFiles = @()

# (a) Authoritative patch file (MUST exist)
$patchPj = Join-Path $scriptDir "patches\product.json"
if (Test-Path $patchPj) {
    $targetFiles += (Get-Item $patchPj)
} else {
    Write-Host "[FAIL] Authoritative product.json missing at: $patchPj" -ForegroundColor Red
    $failureCount++
}

# (b) Packaged root product.json (MUST exist)
$rootPj = Join-Path $PackDir "resources\app\product.json"
if (Test-Path $rootPj) {
    $targetFiles += (Get-Item $rootPj)
} else {
    Write-Host "[FAIL] Packaged root product.json missing at: $rootPj" -ForegroundColor Red
    $failureCount++
}

# (c) All versioned subdirectories in packaging output (MUST exist and contain product.json)
if ($packVersionedDirs.Count -eq 0) {
    if ($mustRequireVersioned) {
        Write-Host "[FAIL] No versioned runtime directories found in $PackDir! Requirement R1 mandates deploying product.json to versioned directories." -ForegroundColor Red
        $failureCount++
    } else {
        Write-Host "[WARN] No versioned runtime directories found in $PackDir" -ForegroundColor Yellow
    }
} else {
    foreach ($vDir in $packVersionedDirs) {
        $vPj = Join-Path $vDir.FullName "resources\app\product.json"
        if (Test-Path $vPj) {
            $targetFiles += (Get-Item $vPj)
        } else {
            Write-Host "[FAIL] Versioned product.json missing in runtime directory: $vPj" -ForegroundColor Red
            $failureCount++
        }
    }
}

# (d) Optional: Check installed IDE product.json files
if ($shouldCheckInstalled) {
    $installedPaths = @()
    if ($env:LOCALAPPDATA) {
        $instBase = Join-Path $env:LOCALAPPDATA "HugOS IDE"
        if (Test-Path $instBase) {
            $instRootPj = Join-Path $instBase "resources\app\product.json"
            if (Test-Path $instRootPj) {
                $installedPaths += $instRootPj
            } else {
                Write-Host "[FAIL] Installed root product.json missing: $instRootPj" -ForegroundColor Red
                $failureCount++
            }
            $instVerDirs = @(Get-ChildItem $instBase -Directory | Where-Object { $_.Name -match '^[0-9a-f]{7,40}$' })
            foreach ($ivd in $instVerDirs) {
                $instVPj = Join-Path $ivd.FullName "resources\app\product.json"
                if (Test-Path $instVPj) {
                    $installedPaths += $instVPj
                } else {
                    Write-Host "[FAIL] Installed versioned product.json missing in runtime directory: $instVPj" -ForegroundColor Red
                    $failureCount++
                }
            }
        }
    }
    foreach ($ip in $installedPaths | Select-Object -Unique) {
        if (Test-Path $ip) {
            $item = Get-Item $ip
            if (-not ($targetFiles | Where-Object { [System.IO.Path]::GetFullPath($_.FullName).ToLower() -eq [System.IO.Path]::GetFullPath($item.FullName).ToLower() })) {
                $targetFiles += $item
            }
        }
    }
}

if ($targetFiles.Count -eq 0) {
    Write-Host "[FAIL] No product.json files found to validate!" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Collected $($targetFiles.Count) product.json file(s) for validation." -ForegroundColor Cyan

# Required API proposals
$requiredProposals = @("defaultChatParticipant", "chatParticipantAdditions")

# Required branding fields and expected values
$requiredBranding = @{
    "nameShort"              = "HugOS"
    "nameLong"               = "HugOS IDE"
    "applicationName"        = "hugos"
    "win32MutexName"         = "hugos"
    "win32DirName"           = "HugOS IDE"
    "win32NameVersion"       = "HugOS IDE"
    "dataFolderName"         = ".hugos-ide"
    "darwinBundleIdentifier" = "com.hugos.ide"
    "win32AppUserModelId"    = "HugOS.HugOS"
    "win32ShellNameShort"    = "H&ugOS"
}

# 4. Validate each file
foreach ($file in $targetFiles) {
    Write-Host "`n------------------------------------------------------------" -ForegroundColor Gray
    Write-Host "[CHECKING] $($file.FullName)" -ForegroundColor White
    Write-Host "------------------------------------------------------------" -ForegroundColor Gray

    # Check (d): Validate clean BOM-free UTF-8 encoding
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    if ($bytes.Length -eq 0) {
        Write-Host "  [FAIL] File is completely empty (0 bytes)" -ForegroundColor Red
        $failureCount++
        continue
    } elseif ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Write-Host "  [FAIL] File contains UTF-8 BOM (Byte Order Mark), breaking Node.js JSON.parse runtime" -ForegroundColor Red
        $failureCount++
    } elseif ($bytes.Length -ge 2 -and (($bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) -or ($bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF))) {
        Write-Host "  [FAIL] File contains UTF-16 BOM, breaking Node.js UTF-8 JSON parsing" -ForegroundColor Red
        $failureCount++
    } else {
        Write-Host "  [PASS] File encoding is clean BOM-free UTF-8" -ForegroundColor Green
    }

    $pj = $null
    try {
        $raw = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
        $pj = $raw | ConvertFrom-Json
    } catch {
        Write-Host "  [FAIL] JSON parsing error in $($file.FullName): $_" -ForegroundColor Red
        $failureCount++
        continue
    }

    if ($null -eq $pj) {
        Write-Host "  [FAIL] File parsed to null / not a valid JSON object: $($file.FullName)" -ForegroundColor Red
        $failureCount++
        continue
    }

    # Check (a): defaultChatAgent.extensionId, chatExtensionId, and chatExtensionOutputId match actual extension ID
    if (-not $pj.defaultChatAgent -or ($pj.defaultChatAgent -isnot [System.Management.Automation.PSCustomObject])) {
        Write-Host "  [FAIL] Missing or invalid 'defaultChatAgent' section in product.json" -ForegroundColor Red
        $failureCount++
    } else {
        $actualExtId = $pj.defaultChatAgent.extensionId
        if ($actualExtId -isnot [string] -or [string]::IsNullOrWhiteSpace($actualExtId)) {
            Write-Host "  [FAIL] defaultChatAgent.extensionId is not a valid non-empty string" -ForegroundColor Red
            $failureCount++
        } elseif ($expectedExtensionId -ne "$actualExtId") {
            Write-Host "  [FAIL] defaultChatAgent.extensionId mismatch! Got: '$actualExtId', Expected: '$expectedExtensionId'" -ForegroundColor Red
            $failureCount++
        } else {
            Write-Host "  [PASS] defaultChatAgent.extensionId matches: '$actualExtId'" -ForegroundColor Green
        }

        $actualChatExtId = $pj.defaultChatAgent.chatExtensionId
        if ($actualChatExtId -isnot [string] -or [string]::IsNullOrWhiteSpace($actualChatExtId)) {
            Write-Host "  [FAIL] defaultChatAgent.chatExtensionId is not a valid non-empty string" -ForegroundColor Red
            $failureCount++
        } elseif ($expectedExtensionId -ne "$actualChatExtId") {
            Write-Host "  [FAIL] defaultChatAgent.chatExtensionId mismatch! Got: '$actualChatExtId', Expected: '$expectedExtensionId'" -ForegroundColor Red
            $failureCount++
        } else {
            Write-Host "  [PASS] defaultChatAgent.chatExtensionId matches: '$actualChatExtId'" -ForegroundColor Green
        }

        $actualOutputId = $pj.defaultChatAgent.chatExtensionOutputId
        if ($actualOutputId -isnot [string] -or [string]::IsNullOrWhiteSpace($actualOutputId)) {
            Write-Host "  [FAIL] Missing or empty defaultChatAgent.chatExtensionOutputId in product.json" -ForegroundColor Red
            $failureCount++
        } else {
            $expectedOutputPrefix = "$expectedExtensionId."
            if (-not $actualOutputId.StartsWith($expectedOutputPrefix)) {
                Write-Host "  [FAIL] defaultChatAgent.chatExtensionOutputId does not start with '$expectedOutputPrefix': '$actualOutputId'" -ForegroundColor Red
                $failureCount++
            } else {
                Write-Host "  [PASS] defaultChatAgent.chatExtensionOutputId matches expected prefix: '$actualOutputId'" -ForegroundColor Green
            }
        }
    }

    # Check (b): extensionEnabledApiProposals contains required proposals
    if (-not $pj.extensionEnabledApiProposals -or ($pj.extensionEnabledApiProposals -isnot [System.Management.Automation.PSCustomObject])) {
        Write-Host "  [FAIL] Missing or invalid 'extensionEnabledApiProposals' in product.json" -ForegroundColor Red
        $failureCount++
    } else {
        $extProposals = $pj.extensionEnabledApiProposals.PSObject.Properties[$expectedExtensionId]
        if (-not $extProposals -or -not $extProposals.Value -or ($extProposals.Value -isnot [System.Collections.IEnumerable]) -or ($extProposals.Value -is [string])) {
            Write-Host "  [FAIL] No valid extensionEnabledApiProposals list found for '$expectedExtensionId'" -ForegroundColor Red
            $failureCount++
        } else {
            $proposalList = @($extProposals.Value)
            Write-Host "  [INFO] '$expectedExtensionId' has $($proposalList.Count) enabled proposals." -ForegroundColor Gray
            foreach ($req in $requiredProposals) {
                if ($proposalList -contains $req) {
                    Write-Host "  [PASS] Contains proposal: '$req'" -ForegroundColor Green
                } else {
                    Write-Host "  [FAIL] Missing required proposal: '$req'" -ForegroundColor Red
                    $failureCount++
                }
            }
        }
    }

    # Check (c): HugOS branding fields are present and valid
    foreach ($entry in $requiredBranding.GetEnumerator()) {
        $field = $entry.Key
        $expectedVal = $entry.Value
        $actualVal = $pj.$field
        if ($actualVal -isnot [string] -or [string]::IsNullOrWhiteSpace($actualVal)) {
            Write-Host "  [FAIL] Missing, non-string, or empty branding field '$field'" -ForegroundColor Red
            $failureCount++
        } elseif ("$actualVal" -ne "$expectedVal") {
            Write-Host "  [FAIL] Branding field '$field' mismatch! Got: '$actualVal', Expected: '$expectedVal'" -ForegroundColor Red
            $failureCount++
        } else {
            Write-Host "  [PASS] Branding field '$field' = '$actualVal'" -ForegroundColor Green
        }
    }

    # Check (f): Upstream Microsoft updates must be completely eliminated / neutralized
    if ($pj.PSObject.Properties['updateUrl'] -and -not [string]::IsNullOrWhiteSpace("$($pj.updateUrl)")) {
        Write-Host "  [FAIL] Upstream updateUrl is active: '$($pj.updateUrl)'. Must be completely removed/neutralized." -ForegroundColor Red
        $failureCount++
    } else {
        Write-Host "  [PASS] Upstream updateUrl is absent / neutralized" -ForegroundColor Green
    }

    if ($pj.PSObject.Properties['quality'] -and -not [string]::IsNullOrWhiteSpace("$($pj.quality)")) {
        Write-Host "  [FAIL] Upstream quality is active: '$($pj.quality)'. Must be completely removed/neutralized." -ForegroundColor Red
        $failureCount++
    } else {
        Write-Host "  [PASS] Upstream quality is absent / neutralized" -ForegroundColor Green
    }

    if (-not $pj.configurationDefaults -or ($pj.configurationDefaults."update.mode" -ne "none")) {
        Write-Host "  [FAIL] configurationDefaults.update.mode is not set to 'none'" -ForegroundColor Red
        $failureCount++
    } else {
        Write-Host "  [PASS] configurationDefaults.update.mode is 'none'" -ForegroundColor Green
    }
}

# 5. Final Report
Write-Host "`n============================================================" -ForegroundColor Cyan
if ($failureCount -eq 0) {
    Write-Host "[SUCCESS] All product.json verification checks PASSED ($($targetFiles.Count) files validated)." -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "[ERROR] Verification FAILED with $failureCount total issue(s) across $($targetFiles.Count) files." -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Cyan
    exit 1
}
