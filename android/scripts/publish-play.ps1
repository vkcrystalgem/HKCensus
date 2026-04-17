param(
  [string]$Track,
  [string]$ReleaseStatus,
  [string]$ReleaseName,
  [string]$AabPath,
  [string]$ReleaseNotesFile,
  [string]$ReleaseNotesLanguage,
  [string]$ReceiptJson,
  [switch]$ChangesNotSentForReview,
  [switch]$QueryNextVersionCode,
  [switch]$Build
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$androidRoot = Split-Path -Parent $scriptDir
$nativeRoot = Join-Path $androidRoot "android"
$commonPath = Join-Path $scriptDir "common.ps1"
. $commonPath

Set-HKCensusToolchainEnvironment $androidRoot | Out-Null
Set-HKCensusReleaseEnvironment $androidRoot @{
  PLAY_TRACK = $Track
  PLAY_RELEASE_STATUS = $ReleaseStatus
  PLAY_RELEASE_NAME = $ReleaseName
  AAB_PATH = $AabPath
  PLAY_RELEASE_NOTES_FILE = $ReleaseNotesFile
  PLAY_RELEASE_NOTES_LANGUAGE = $ReleaseNotesLanguage
  PLAY_RECEIPT_JSON = $ReceiptJson
} | Out-Null

$serviceAccount = Get-HKCensusEnvValue "HKCENSUS_PLAY_SERVICE_ACCOUNT_JSON"
if ([string]::IsNullOrWhiteSpace($serviceAccount)) {
  throw "Missing PLAY_SERVICE_ACCOUNT_JSON in android/release.properties or the current environment."
}
$serviceAccount = Resolve-HKCensusPath $androidRoot $serviceAccount
Set-Item -Path "Env:HKCENSUS_PLAY_SERVICE_ACCOUNT_JSON" -Value $serviceAccount

if ($Build) {
  & (Join-Path $scriptDir "build-release.ps1") -BundleOnly
  if ($LASTEXITCODE -ne 0) {
    throw "Release bundle build failed."
  }
}

$aabEnv = Get-HKCensusEnvValue "HKCENSUS_AAB_PATH"
if ([string]::IsNullOrWhiteSpace($aabEnv)) {
  $aabEnv = Join-Path $nativeRoot "app\\build\\outputs\\bundle\\release\\app-release.aab"
}
$aabEnv = Resolve-HKCensusPath $androidRoot $aabEnv
Set-Item -Path "Env:HKCENSUS_AAB_PATH" -Value $aabEnv

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  throw "Python is required to publish to Google Play. Install Python and 'pip install -r android/requirements-publish.txt'."
}

$pythonArgs = @((Join-Path $scriptDir "publish_play.py"))
if ($QueryNextVersionCode) {
  $pythonArgs += "--query-next-version-code"
}
if ($ChangesNotSentForReview) {
  $pythonArgs += "--changes-not-sent-for-review"
}
& $python.Source @pythonArgs
if ($LASTEXITCODE -ne 0) {
  throw "Google Play upload failed."
}
