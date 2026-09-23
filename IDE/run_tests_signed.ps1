$pfxPath = "IDE\hugos-signing-cert.pfx"
$password = "HugOSPassword123!"
$pwdSecure = ConvertTo-SecureString $password -AsPlainText -Force
$signCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($pfxPath, $pwdSecure)

$testExes = Get-ChildItem -Path "target\release\deps\cli-*.exe"
foreach ($exe in $testExes) {
    Set-AuthenticodeSignature -FilePath $exe.FullName -Certificate $signCert -HashAlgorithm SHA256 | Out-Null
    Write-Host "Signed $($exe.Name)"
}

# Run unit tests from cli-8014aac6cf1481cd.exe
& "target\release\deps\cli-8014aac6cf1481cd.exe" -- prompt_interception_tests::
