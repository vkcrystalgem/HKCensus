param(
  [string]$VersionCode,
  [string]$VersionName,
  [switch]$SkipPrebuild,
  [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$androidRoot = Split-Path -Parent $scriptDir
$nativeRoot = Join-Path $androidRoot "android"
$commonPath = Join-Path $androidRoot "scripts\common.ps1"
. $commonPath

$appConfig = Get-Content -LiteralPath (Join-Path $androidRoot "app.json") -Raw | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($VersionCode)) {
  $VersionCode = [string]$appConfig.expo.android.versionCode
}
if ([string]::IsNullOrWhiteSpace($VersionName)) {
  $VersionName = [string]$appConfig.expo.version
}

$toolchain = Set-HKCensusToolchainEnvironment $androidRoot
Set-HKCensusReleaseEnvironment $androidRoot @{
  VERSION_CODE = $VersionCode
  VERSION_NAME = $VersionName
} | Out-Null

if ([string]::IsNullOrWhiteSpace($env:NODE_ENV)) {
  $env:NODE_ENV = "production"
}

$requiredRelease = @("KEYSTORE_FILE", "KEYSTORE_PASSWORD", "KEY_ALIAS", "KEY_PASSWORD")
$requiredDebug = @("DEBUG_KEYSTORE_FILE", "DEBUG_KEYSTORE_PASSWORD", "DEBUG_KEY_ALIAS", "DEBUG_KEY_PASSWORD")

foreach ($required in $requiredRelease + $requiredDebug) {
  $value = Get-HKCensusEnvValue "HKCENSUS_$required"
  if ([string]::IsNullOrWhiteSpace($value)) {
    throw "Missing $required. Provide it in android/release.properties, HKCENSUS_$required, or the corresponding ANDROID_* environment variable."
  }
}

$releaseKeystoreFile = Resolve-HKCensusPath $androidRoot (Get-HKCensusEnvValue "HKCENSUS_KEYSTORE_FILE")
$releaseKeystorePassword = Get-HKCensusEnvValue "HKCENSUS_KEYSTORE_PASSWORD"
$releaseKeyAlias = Get-HKCensusEnvValue "HKCENSUS_KEY_ALIAS"
$releaseKeyPassword = Get-HKCensusEnvValue "HKCENSUS_KEY_PASSWORD"
$debugKeystoreFile = Resolve-HKCensusPath $androidRoot (Get-HKCensusEnvValue "HKCENSUS_DEBUG_KEYSTORE_FILE")
$debugKeystorePassword = Get-HKCensusEnvValue "HKCENSUS_DEBUG_KEYSTORE_PASSWORD"
$debugKeyAlias = Get-HKCensusEnvValue "HKCENSUS_DEBUG_KEY_ALIAS"
$debugKeyPassword = Get-HKCensusEnvValue "HKCENSUS_DEBUG_KEY_PASSWORD"

if (-not $SkipPrebuild) {
  Push-Location $androidRoot
  try {
    & $toolchain.Npx "expo" "prebuild" "--platform" "android" "--no-install"
    if ($LASTEXITCODE -ne 0) {
      throw "Expo prebuild failed."
    }
  } finally {
    Pop-Location
  }
}

Push-Location $nativeRoot
try {
  if ($Clean) {
    & ".\\gradlew.bat" "clean" "--no-daemon"
    if ($LASTEXITCODE -ne 0) {
      throw "Gradle clean failed."
    }
  }

  & ".\\gradlew.bat" "assembleRelease" "bundleRelease" "assembleDebug" "bundleDebug" "--no-daemon"
  if ($LASTEXITCODE -ne 0) {
    throw "Gradle variant build failed."
  }
} finally {
  Pop-Location
}

$outputDir = Join-Path $scriptDir "out"
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$artifacts = @(
  @{
    Source = Join-Path $nativeRoot "app\\build\\outputs\\apk\\release\\app-release.apk"
    Destination = Join-Path $outputDir "hkcensus-release.apk"
    Label = "Release APK"
  },
  @{
    Source = Join-Path $nativeRoot "app\\build\\outputs\\bundle\\release\\app-release.aab"
    Destination = Join-Path $outputDir "hkcensus-release.aab"
    Label = "Release AAB"
  },
  @{
    Source = Join-Path $nativeRoot "app\\build\\outputs\\apk\\debug\\app-debug.apk"
    Destination = Join-Path $outputDir "hkcensus-debug.apk"
    Label = "Debug APK"
  },
  @{
    Source = Join-Path $nativeRoot "app\\build\\outputs\\bundle\\debug\\app-debug.aab"
    Destination = Join-Path $outputDir "hkcensus-debug.aab"
    Label = "Debug AAB"
  }
)

foreach ($artifact in $artifacts) {
  if (-not (Test-Path $artifact.Source)) {
    throw "Expected artifact missing: $($artifact.Source)"
  }
  Copy-Item -LiteralPath $artifact.Source -Destination $artifact.Destination -Force
  Write-Host "$($artifact.Label): $($artifact.Destination)"
}

$jarsigner = Join-Path $env:JAVA_HOME "bin\jarsigner.exe"
if (-not (Test-Path $jarsigner)) {
  throw "jarsigner not found: $jarsigner"
}

function Test-HKCensusJarSigned([string]$PathToJar) {
  $verifyOutput = & $jarsigner -verify -verbose -certs $PathToJar 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "jarsigner verification failed for $PathToJar"
  }
  return -not ($verifyOutput -match "jar is unsigned\.")
}

function Ensure-HKCensusSignedBundle(
  [string]$BundlePath,
  [string]$KeystoreFile,
  [string]$KeystorePassword,
  [string]$KeyAlias,
  [string]$KeyPassword
) {
  if (Test-HKCensusJarSigned $BundlePath) {
    return
  }

  & $jarsigner `
    -sigalg "SHA256withRSA" `
    -digestalg "SHA-256" `
    -keystore $KeystoreFile `
    -storepass $KeystorePassword `
    -keypass $KeyPassword `
    $BundlePath `
    $KeyAlias
  if ($LASTEXITCODE -ne 0) {
    throw "jarsigner failed for $BundlePath"
  }

  if (-not (Test-HKCensusJarSigned $BundlePath)) {
    throw "Bundle is still unsigned after jarsigner: $BundlePath"
  }
}

Ensure-HKCensusSignedBundle (Join-Path $outputDir "hkcensus-release.aab") $releaseKeystoreFile $releaseKeystorePassword $releaseKeyAlias $releaseKeyPassword
Ensure-HKCensusSignedBundle (Join-Path $outputDir "hkcensus-debug.aab") $debugKeystoreFile $debugKeystorePassword $debugKeyAlias $debugKeyPassword
