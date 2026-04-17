param(
  [string]$VersionCode,
  [string]$VersionName,
  [switch]$SkipPrebuild,
  [switch]$BundleOnly,
  [switch]$ApkOnly,
  [switch]$Clean
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$androidRoot = Split-Path -Parent $scriptDir
$nativeRoot = Join-Path $androidRoot "android"
$commonPath = Join-Path $scriptDir "common.ps1"
. $commonPath

$toolchain = Set-HKCensusToolchainEnvironment $androidRoot
$releaseFile = Set-HKCensusReleaseEnvironment $androidRoot @{
  VERSION_CODE = $VersionCode
  VERSION_NAME = $VersionName
}

if ([string]::IsNullOrWhiteSpace($env:NODE_ENV)) {
  $env:NODE_ENV = "production"
}

foreach ($required in "KEYSTORE_FILE", "KEYSTORE_PASSWORD", "KEY_ALIAS", "KEY_PASSWORD") {
  $value = Get-HKCensusEnvValue "HKCENSUS_$required"
  if ([string]::IsNullOrWhiteSpace($value)) {
    throw "Missing $required. Provide it in android/release.properties, HKCENSUS_$required, or the legacy ANDROID_* environment variables."
  }
}

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

  $tasks = @()
  if (-not $BundleOnly) {
    $tasks += "assembleRelease"
  }
  if (-not $ApkOnly) {
    $tasks += "bundleRelease"
  }
  if (-not $tasks.Count) {
    throw "Nothing to build. Do not use -BundleOnly and -ApkOnly together."
  }

  & ".\\gradlew.bat" @tasks "--no-daemon"
  if ($LASTEXITCODE -ne 0) {
    throw "Gradle release build failed."
  }
} finally {
  Pop-Location
}

$apkPath = Join-Path $nativeRoot "app\\build\\outputs\\apk\\release\\app-release.apk"
$aabPath = Join-Path $nativeRoot "app\\build\\outputs\\bundle\\release\\app-release.aab"

if (Test-Path $apkPath) {
  Write-Host "Release APK: $apkPath"
}
if (Test-Path $aabPath) {
  Write-Host "Release AAB: $aabPath"
}
