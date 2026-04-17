param(
  [string]$KeystoreFile = "C:\github\android-my-keystore\my-release-key.keystore",
  [string]$KeystorePassword = "android",
  [string]$KeyAlias = "androiddebugkey",
  [string]$KeyPassword = "android",
  [string]$VersionCode = "900001",
  [string]$VersionName = "1.0.0-ownership-proof"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$androidRoot = Split-Path -Parent $scriptDir
$commonPath = Join-Path $androidRoot "scripts\common.ps1"
. $commonPath

$expectedFingerprint = "FA:C6:17:45:DC:09:03:78:6F:B9:ED:E6:2A:96:2B:39:9F:73:48:F0:BB:6F:89:9B:83:32:66:75:91:03:3B:9C"
$registrationFile = Join-Path $scriptDir "adi-registration.properties"
$buildScript = Join-Path $androidRoot "scripts\build-release.ps1"
$sourceApk = Join-Path $androidRoot "android\app\build\outputs\apk\release\app-release.apk"
$outDir = Join-Path $scriptDir "out"
$outputApk = Join-Path $outDir "hkcensus-ownership-proof.apk"

if (-not (Test-Path $registrationFile)) {
  throw "Missing $registrationFile. Create it from adi-registration.properties.example and paste the Google-provided ADI token into it."
}

$registrationToken = (Get-Content -LiteralPath $registrationFile -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($registrationToken)) {
  throw "The registration token file is empty: $registrationFile"
}

if (-not (Test-Path $KeystoreFile)) {
  throw "Keystore not found: $KeystoreFile"
}

$javaHome = Resolve-HKCensusJavaHome
if (-not $javaHome) {
  throw "Unable to locate a supported JDK 17-21 for keytool."
}

$keytool = Join-Path $javaHome "bin\keytool.exe"
if (-not (Test-Path $keytool)) {
  throw "keytool not found: $keytool"
}

$keytoolStdOut = [System.IO.Path]::GetTempFileName()
$keytoolStdErr = [System.IO.Path]::GetTempFileName()
try {
  $keytoolProcess = Start-Process -FilePath $keytool `
    -ArgumentList @("-list", "-v", "-keystore", $KeystoreFile, "-storepass", $KeystorePassword, "-alias", $KeyAlias, "-keypass", $KeyPassword) `
    -Wait -NoNewWindow -PassThru `
    -RedirectStandardOutput $keytoolStdOut `
    -RedirectStandardError $keytoolStdErr
  $fingerprintExitCode = $keytoolProcess.ExitCode
  $fingerprintOutput = @(
    if (Test-Path $keytoolStdOut) { Get-Content -LiteralPath $keytoolStdOut }
    if (Test-Path $keytoolStdErr) { Get-Content -LiteralPath $keytoolStdErr }
  )
} finally {
  Remove-Item -LiteralPath $keytoolStdOut, $keytoolStdErr -Force -ErrorAction SilentlyContinue
}

if ($fingerprintExitCode -ne 0) {
  throw "keytool failed while reading the keystore."
}

$shaLine = ($fingerprintOutput | Select-String "SHA256:" | Select-Object -First 1)
if (-not $shaLine) {
  throw "Could not read the SHA-256 fingerprint from $KeystoreFile"
}

$actualFingerprint = ($shaLine.ToString() -replace ".*SHA256:\s*", "").Trim()
if ($actualFingerprint -ne $expectedFingerprint) {
  throw "Keystore fingerprint mismatch. Expected $expectedFingerprint but found $actualFingerprint"
}

Set-Item -Path "Env:HKCENSUS_ADI_REGISTRATION_FILE" -Value $registrationFile
Set-Item -Path "Env:HKCENSUS_KEYSTORE_FILE" -Value $KeystoreFile
Set-Item -Path "Env:HKCENSUS_KEYSTORE_PASSWORD" -Value $KeystorePassword
Set-Item -Path "Env:HKCENSUS_KEY_ALIAS" -Value $KeyAlias
Set-Item -Path "Env:HKCENSUS_KEY_PASSWORD" -Value $KeyPassword

& $buildScript -ApkOnly -Clean -VersionCode $VersionCode -VersionName $VersionName
if ($LASTEXITCODE -ne 0) {
  throw "APK build failed."
}

if (-not (Test-Path $sourceApk)) {
  throw "Expected APK not found: $sourceApk"
}

New-Item -ItemType Directory -Path $outDir -Force | Out-Null
Copy-Item -LiteralPath $sourceApk -Destination $outputApk -Force

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($outputApk)
try {
  $entry = $zip.Entries | Where-Object { $_.FullName -eq "assets/adi-registration.properties" } | Select-Object -First 1
  if (-not $entry) {
    throw "The generated APK does not contain assets/adi-registration.properties"
  }

  $reader = New-Object System.IO.StreamReader($entry.Open())
  try {
    $apkToken = $reader.ReadToEnd().Trim()
  } finally {
    $reader.Dispose()
  }

  if ($apkToken -ne $registrationToken) {
    throw "The token embedded in the APK does not match $registrationFile"
  }
} finally {
  $zip.Dispose()
}

$buildToolsRoot = Join-Path $env:LOCALAPPDATA "Android\Sdk\build-tools"
$apksigner = $null
if (Test-Path $buildToolsRoot) {
  $apksigner = Get-ChildItem -Path $buildToolsRoot -Directory |
    Sort-Object Name -Descending |
    ForEach-Object { Join-Path $_.FullName "apksigner.bat" } |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1
}

if ($apksigner) {
  $apksignerStdOut = [System.IO.Path]::GetTempFileName()
  $apksignerStdErr = [System.IO.Path]::GetTempFileName()
  try {
    $apksignerProcess = Start-Process -FilePath $apksigner `
      -ArgumentList @("verify", "--print-certs", $outputApk) `
      -Wait -NoNewWindow -PassThru `
      -RedirectStandardOutput $apksignerStdOut `
      -RedirectStandardError $apksignerStdErr
    $verifyExitCode = $apksignerProcess.ExitCode
    $verifyOutput = @(
      if (Test-Path $apksignerStdOut) { Get-Content -LiteralPath $apksignerStdOut }
      if (Test-Path $apksignerStdErr) { Get-Content -LiteralPath $apksignerStdErr }
    )
  } finally {
    Remove-Item -LiteralPath $apksignerStdOut, $apksignerStdErr -Force -ErrorAction SilentlyContinue
  }
  if ($verifyExitCode -ne 0) {
    throw "apksigner verification failed for $outputApk"
  }
  $apkDigestLine = ($verifyOutput | Select-String "certificate SHA-256 digest:" | Select-Object -First 1)
  if ($apkDigestLine) {
    $apkDigest = ($apkDigestLine.ToString() -replace ".*certificate SHA-256 digest:\s*", "").Trim().ToUpperInvariant()
    $expectedApkDigest = ($expectedFingerprint -replace ":", "").ToUpperInvariant()
    if ($apkDigest -ne $expectedApkDigest) {
      throw "APK signer mismatch. Expected $expectedApkDigest but found $apkDigest"
    }
  }
  $verifyOutput | Write-Host
}

Write-Host "Ownership proof APK: $outputApk"
Write-Host "Verified SHA-256: $actualFingerprint"
