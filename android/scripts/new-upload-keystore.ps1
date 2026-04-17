param(
  [string]$KeystorePath,
  [string]$KeyAlias = "upload",
  [string]$StorePassword,
  [string]$KeyPassword,
  [string]$VersionCode = "1",
  [string]$VersionName = "1.0.0",
  [string]$DName = "CN=HK Census, OU=Mobile, O=VK Crystal Gem, L=Hong Kong, ST=Hong Kong, C=HK",
  [switch]$Force
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$androidRoot = Split-Path -Parent $scriptDir
$commonPath = Join-Path $scriptDir "common.ps1"
. $commonPath

function New-HKCensusSecret([int]$Length = 24) {
  $chars = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@$%*+-_=?"
  $buffer = New-Object byte[] ($Length * 2)
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
  $builder = New-Object System.Text.StringBuilder
  for ($i = 0; $i -lt $Length; $i++) {
    [void]$builder.Append($chars[$buffer[$i] % $chars.Length])
  }
  return $builder.ToString()
}

$toolchain = Set-HKCensusToolchainEnvironment $androidRoot

if (-not $KeystorePath) {
  $KeystorePath = Join-Path $androidRoot "keys\\upload-keystore.jks"
}
if (-not [System.IO.Path]::IsPathRooted($KeystorePath)) {
  $KeystorePath = Join-Path $androidRoot $KeystorePath
}

if (-not $StorePassword) {
  $StorePassword = New-HKCensusSecret
}
if (-not $KeyPassword) {
  $KeyPassword = New-HKCensusSecret
}

$keystoreDir = Split-Path -Parent $KeystorePath
New-Item -ItemType Directory -Path $keystoreDir -Force | Out-Null

if ((Test-Path $KeystorePath) -and -not $Force) {
  Write-Host "Reusing existing upload keystore: $KeystorePath"
} else {
  if ((Test-Path $KeystorePath) -and $Force) {
    Remove-Item -LiteralPath $KeystorePath -Force
  }

  $keytoolSource = (Get-Command keytool | Select-Object -ExpandProperty Source)
  & $keytoolSource `
    -genkeypair `
    -v `
    -storetype JKS `
    -keystore $KeystorePath `
    -alias $KeyAlias `
    -keyalg RSA `
    -keysize 4096 `
    -validity 10000 `
    -storepass $StorePassword `
    -keypass $KeyPassword `
    -dname $DName

  if ($LASTEXITCODE -ne 0) {
    throw "keytool failed while creating the upload keystore."
  }
}

$releasePropertiesPath = Join-Path $androidRoot "release.properties"
$resolvedKeystore = (Resolve-Path -LiteralPath $KeystorePath).Path
$normalizedKeystore = $resolvedKeystore -replace "\\", "/"
$releaseProperties = @(
  "# Generated locally by scripts/new-upload-keystore.ps1"
  "VERSION_CODE=$VersionCode"
  "VERSION_NAME=$VersionName"
  "KEYSTORE_FILE=$normalizedKeystore"
  "KEYSTORE_PASSWORD=$StorePassword"
  "KEY_ALIAS=$KeyAlias"
  "KEY_PASSWORD=$KeyPassword"
  "PLAY_SERVICE_ACCOUNT_JSON=play/service-account.json"
  "PLAY_TRACK=internal"
  "PLAY_RELEASE_STATUS=draft"
  "PLAY_RELEASE_NAME=HK Census $VersionName"
)
[System.IO.File]::WriteAllLines($releasePropertiesPath, $releaseProperties)

Write-Host "Created upload keystore: $KeystorePath"
Write-Host "Wrote local release properties: $releasePropertiesPath"
Write-Host "Back up both files securely before uploading any release to Google Play."
