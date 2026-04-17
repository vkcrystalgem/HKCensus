param(
  [string]$Track,
  [string]$ReleaseStatus,
  [string]$ReleaseName,
  [string]$VersionName,
  [int]$VersionCode,
  [string]$AabPath,
  [string]$ReleaseNotesFile,
  [string]$ReleaseNotesLanguage,
  [switch]$SkipBuild,
  [switch]$SkipTests,
  [switch]$SkipTypecheck,
  [switch]$SkipVersionCodeQuery,
  [switch]$ChangesNotSentForReview,
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$androidRoot = Split-Path -Parent $scriptDir
$commonPath = Join-Path $androidRoot "scripts\common.ps1"
. $commonPath

$toolchain = Set-HKCensusToolchainEnvironment $androidRoot
Set-HKCensusReleaseEnvironment $androidRoot @{
  PLAY_TRACK = $Track
  PLAY_RELEASE_STATUS = $ReleaseStatus
  PLAY_RELEASE_NAME = $ReleaseName
  PLAY_RELEASE_NOTES_FILE = $ReleaseNotesFile
  PLAY_RELEASE_NOTES_LANGUAGE = $ReleaseNotesLanguage
} | Out-Null

$appConfig = Get-Content -LiteralPath (Join-Path $androidRoot "app.json") -Raw | ConvertFrom-Json
$packageName = [string]$appConfig.expo.android.package
$localVersionCode = [int]$appConfig.expo.android.versionCode
$resolvedVersionName = if ([string]::IsNullOrWhiteSpace($VersionName)) { [string]$appConfig.expo.version } else { $VersionName }
$resolvedTrack = Get-HKCensusEnvValue "HKCENSUS_PLAY_TRACK"
if ([string]::IsNullOrWhiteSpace($resolvedTrack)) {
  $resolvedTrack = "internal"
}
$resolvedReleaseStatus = Get-HKCensusEnvValue "HKCENSUS_PLAY_RELEASE_STATUS"
if ([string]::IsNullOrWhiteSpace($resolvedReleaseStatus)) {
  $resolvedReleaseStatus = "completed"
}
$resolvedReleaseNotesLanguage = Get-HKCensusEnvValue "HKCENSUS_PLAY_RELEASE_NOTES_LANGUAGE"
if ([string]::IsNullOrWhiteSpace($resolvedReleaseNotesLanguage)) {
  $resolvedReleaseNotesLanguage = "en-US"
}
$resolvedReleaseNotesFile = Get-HKCensusEnvValue "HKCENSUS_PLAY_RELEASE_NOTES_FILE"
$serviceAccount = Get-HKCensusEnvValue "HKCENSUS_PLAY_SERVICE_ACCOUNT_JSON"
if (-not [string]::IsNullOrWhiteSpace($serviceAccount)) {
  $serviceAccount = Resolve-HKCensusPath $androidRoot $serviceAccount
  Set-Item -Path "Env:HKCENSUS_PLAY_SERVICE_ACCOUNT_JSON" -Value $serviceAccount
}

$outDir = Join-Path $scriptDir "out"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$queryReceipt = Join-Path $outDir "next-version-code.json"

if (-not $VersionCode) {
  if ($SkipVersionCodeQuery) {
    $VersionCode = $localVersionCode
  } else {
    if ([string]::IsNullOrWhiteSpace($serviceAccount)) {
      throw "Missing PLAY_SERVICE_ACCOUNT_JSON. Set it locally or pass -SkipVersionCodeQuery/-VersionCode."
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
      throw "Python is required for Google Play automation."
    }

    Push-Location $androidRoot
    try {
      $queryOutput = & $python.Source (Join-Path $androidRoot "scripts\publish_play.py") "--query-next-version-code" "--receipt-json" $queryReceipt
      if ($LASTEXITCODE -ne 0) {
        throw "Failed to query Google Play for the next version code."
      }
    } finally {
      Pop-Location
    }

    $queryText = ($queryOutput | Out-String).Trim()
    $lastLine = ($queryText -split "(\r?\n)") | Where-Object { $_ -and $_.Trim() } | Select-Object -Last 1
    $parsedVersionCode = 0
    if (-not [int]::TryParse($lastLine, [ref]$parsedVersionCode)) {
      throw "Could not parse the next version code from Google Play output: $queryText"
    }
    $VersionCode = $parsedVersionCode
  }
}

if ([string]::IsNullOrWhiteSpace($ReleaseName)) {
  $resolvedReleaseName = "HK Census $resolvedVersionName ($VersionCode)"
} else {
  $resolvedReleaseName = $ReleaseName
}

$resolvedAabPath = if ([string]::IsNullOrWhiteSpace($AabPath)) {
  Join-Path $androidRoot "android\app\build\outputs\bundle\release\app-release.aab"
} else {
  Resolve-HKCensusPath $androidRoot $AabPath
}
$receiptJson = Join-Path $outDir ("play-release-{0}.json" -f $VersionCode)

if (-not $SkipTests) {
  & (Join-Path $androidRoot "scripts\use-node.ps1") "test"
  if ($LASTEXITCODE -ne 0) {
    throw "Jest tests failed."
  }
}

if (-not $SkipTypecheck) {
  & (Join-Path $androidRoot "scripts\use-node.ps1") "typecheck"
  if ($LASTEXITCODE -ne 0) {
    throw "TypeScript typecheck failed."
  }
}

if (-not $SkipBuild) {
  & (Join-Path $androidRoot "scripts\build-release.ps1") -BundleOnly -VersionCode ([string]$VersionCode) -VersionName $resolvedVersionName
  if ($LASTEXITCODE -ne 0) {
    throw "Release bundle build failed."
  }
}

if (-not (Test-Path $resolvedAabPath)) {
  throw "Release AAB not found: $resolvedAabPath"
}

$summary = [ordered]@{
  packageName = $packageName
  track = $resolvedTrack
  releaseStatus = $resolvedReleaseStatus
  releaseName = $resolvedReleaseName
  versionCode = $VersionCode
  versionName = $resolvedVersionName
  aabPath = $resolvedAabPath
  releaseNotesFile = $resolvedReleaseNotesFile
  releaseNotesLanguage = $resolvedReleaseNotesLanguage
  changesNotSentForReview = [bool]$ChangesNotSentForReview
  generatedAtUtc = [DateTime]::UtcNow.ToString("o")
}

if ($DryRun) {
  $summary["mode"] = "dry-run"
  ($summary | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $receiptJson -Encoding utf8
  Write-Host "Dry run receipt: $receiptJson"
  Write-Host ($summary | ConvertTo-Json -Depth 5)
  exit 0
}

if ([string]::IsNullOrWhiteSpace($serviceAccount)) {
  throw "Missing PLAY_SERVICE_ACCOUNT_JSON. Set it locally before publishing."
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  throw "Python is required for Google Play automation."
}

$pythonArgs = @(
  (Join-Path $androidRoot "scripts\publish_play.py"),
  "--aab", $resolvedAabPath,
  "--track", $resolvedTrack,
  "--release-status", $resolvedReleaseStatus,
  "--release-name", $resolvedReleaseName,
  "--receipt-json", $receiptJson
)
if (-not [string]::IsNullOrWhiteSpace($resolvedReleaseNotesFile)) {
  $pythonArgs += @("--release-notes-file", (Resolve-HKCensusPath $androidRoot $resolvedReleaseNotesFile))
  $pythonArgs += @("--release-notes-language", $resolvedReleaseNotesLanguage)
}
if ($ChangesNotSentForReview) {
  $pythonArgs += "--changes-not-sent-for-review"
}

Push-Location $androidRoot
try {
  & $python.Source @pythonArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Google Play publish failed."
  }
} finally {
  Pop-Location
}

Write-Host "Publish receipt: $receiptJson"
