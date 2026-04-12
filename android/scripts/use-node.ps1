param(
  [Parameter(Position = 0)]
  [ValidateSet("node", "npm", "npx", "install", "test", "typecheck", "android", "ios", "start", "sync-data")]
  [string]$Command = "node",

  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = "Stop"

function Test-JavaHome([string]$Path) {
  if (-not $Path) {
    return $false
  }
  return (Test-Path (Join-Path $Path 'bin\java.exe'))
}

function Get-JavaMajorVersion([string]$Path) {
  try {
    $line = & (Join-Path $Path 'bin\java.exe') -version 2>&1 | Select-Object -First 1
    if (-not $line) {
      return $null
    }
    $text = $line.ToString()
    if ($text -match '"(?<version>[^"]+)"') {
      $version = $Matches.version
      if ($version.StartsWith('1.')) {
        return [int]($version.Split('.')[1])
      }
      return [int]($version.Split('.')[0])
    }
  } catch {
    return $null
  }
  return $null
}

function Resolve-JavaHome {
  $studioJbr = 'C:\Program Files\Android\Android Studio\jbr'

  if (Test-JavaHome $env:HKCENSUS_JAVA_HOME) {
    return $env:HKCENSUS_JAVA_HOME
  }

  if (Test-JavaHome $studioJbr) {
    return $studioJbr
  }

  if (Test-JavaHome $env:JAVA_HOME) {
    $major = Get-JavaMajorVersion $env:JAVA_HOME
    if ($major -and $major -ge 17 -and $major -le 21) {
      return $env:JAVA_HOME
    }
  }

  $candidates = foreach ($root in @('C:\Program Files\Eclipse Adoptium', 'C:\Program Files\Java')) {
    if (Test-Path $root) {
      Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-JavaHome $_.FullName } |
        ForEach-Object {
          $major = Get-JavaMajorVersion $_.FullName
          if ($major -and $major -ge 17 -and $major -le 21) {
            [PSCustomObject]@{
              Path = $_.FullName
              Major = $major
            }
          }
        }
    }
  }

  return ($candidates | Sort-Object Major -Descending | Select-Object -First 1).Path
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$androidRoot = Split-Path -Parent $scriptDir
$toolRoot = Join-Path $androidRoot '.tooling'
$versionFile = Join-Path $androidRoot '.nvmrc'

if (-not (Test-Path $versionFile)) {
  throw "Missing Node version file: $versionFile"
}

$requestedVersion = (Get-Content -LiteralPath $versionFile -Raw).Trim()
if (-not $requestedVersion) {
  throw "Node version file is empty: $versionFile"
}

$nodeDir = Join-Path $toolRoot "node-v$requestedVersion-win-x64"
$nodeExe = Join-Path $nodeDir 'node.exe'
$npmCmd = Join-Path $nodeDir 'npm.cmd'
$npxCmd = Join-Path $nodeDir 'npx.cmd'

if (-not (Test-Path $nodeExe)) {
  New-Item -ItemType Directory -Path $toolRoot -Force | Out-Null
  $zipName = "node-v$requestedVersion-win-x64.zip"
  $zipPath = Join-Path $toolRoot $zipName
  $downloadUrl = "https://nodejs.org/dist/v$requestedVersion/$zipName"

  Write-Host "Downloading Node.js v$requestedVersion from $downloadUrl"
  Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
  Expand-Archive -LiteralPath $zipPath -DestinationPath $toolRoot -Force
  Remove-Item -LiteralPath $zipPath -Force
}

$javaHome = Resolve-JavaHome
if ($javaHome) {
  $env:JAVA_HOME = $javaHome
  $env:Path = "$javaHome\bin;$nodeDir;$env:Path"
  Write-Host "Using JAVA_HOME=$javaHome"
} else {
  $env:Path = "$nodeDir;$env:Path"
  Write-Warning 'No supported JDK 17-21 was found. Android builds may fail until JAVA_HOME points to a supported JDK.'
}

switch ($Command) {
  'node' {
    & $nodeExe @Args
  }
  'npm' {
    & $npmCmd @Args
  }
  'npx' {
    & $npxCmd @Args
  }
  'install' {
    & $npmCmd 'install' @Args
  }
  'test' {
    & $npmCmd 'test' @Args
  }
  'typecheck' {
    & $npmCmd 'run' 'typecheck' @Args
  }
  'android' {
    & $npmCmd 'run' 'android' @Args
  }
  'ios' {
    & $npmCmd 'run' 'ios' @Args
  }
  'start' {
    & $npmCmd 'start' @Args
  }
  'sync-data' {
    & $npmCmd 'run' 'sync-data' @Args
  }
}

exit $LASTEXITCODE