$pfxPath = "IDE\hugos-signing-cert.pfx"
$password = "HugOSPassword123!"
$pwdSecure = ConvertTo-SecureString $password -AsPlainText -Force
$signCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($pfxPath, $pwdSecure)

$testExes = Get-ChildItem -Path "target\release\deps\cli-*.exe" | Sort-Object LastWriteTime -Descending
foreach ($exe in $testExes) {
    Set-AuthenticodeSignature -FilePath $exe.FullName -Certificate $signCert -HashAlgorithm SHA256 | Out-Null
    Write-Host "Signed $($exe.Name)"
}

# Find the test harness binary (it supports --list)
$testHarness = $null
foreach ($exe in $testExes) {
    $out = & $exe.FullName --list 2>$null
    if ($out -match "prompt_interception_tests::") {
        $testHarness = $exe
        break
    }
}

if ($testHarness) {
    Write-Host "Running tests from $($testHarness.FullName)"
    & $testHarness.FullName -- prompt_interception_tests::
} else {
    Write-Error "No test harness binary found"
}
