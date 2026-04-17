Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-HKCensusJavaHome([string]$Path) {
  if (-not $Path) {
    return $false
  }
  return (Test-Path (Join-Path $Path "bin\\java.exe"))
}

function Get-HKCensusJavaMajorVersion([string]$Path) {
  try {
    $line = & (Join-Path $Path "bin\\java.exe") -version 2>&1 | Select-Object -First 1
    if (-not $line) {
      return $null
    }
    $text = $line.ToString()
    if ($text -match '"(?<version>[^"]+)"') {
      $version = $Matches.version
      if ($version.StartsWith("1.")) {
        return [int]($version.Split(".")[1])
      }
      return [int]($version.Split(".")[0])
    }
  } catch {
    return $null
  }
  return $null
}

function Resolve-HKCensusJavaHome {
  $studioJbr = "C:\Program Files\Android\Android Studio\jbr"

  if (Test-HKCensusJavaHome $env:HKCENSUS_JAVA_HOME) {
    return $env:HKCENSUS_JAVA_HOME
  }

  if (Test-HKCensusJavaHome $studioJbr) {
    return $studioJbr
  }

  if (Test-HKCensusJavaHome $env:JAVA_HOME) {
    $major = Get-HKCensusJavaMajorVersion $env:JAVA_HOME
    if ($major -and $major -ge 17 -and $major -le 21) {
      return $env:JAVA_HOME
    }
  }

  $candidates = foreach ($root in @("C:\Program Files\Eclipse Adoptium", "C:\Program Files\Java")) {
    if (Test-Path $root) {
      Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-HKCensusJavaHome $_.FullName } |
        ForEach-Object {
          $major = Get-HKCensusJavaMajorVersion $_.FullName
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

function Get-HKCensusNodeVersion([string]$AndroidRoot) {
  $versionFile = Join-Path $AndroidRoot ".nvmrc"
  if (-not (Test-Path $versionFile)) {
    throw "Missing Node version file: $versionFile"
  }
  $version = (Get-Content -LiteralPath $versionFile -Raw).Trim()
  if (-not $version) {
    throw "Node version file is empty: $versionFile"
  }
  return $version
}

function Initialize-HKCensusNodeToolchain([string]$AndroidRoot) {
  $toolRoot = Join-Path $AndroidRoot ".tooling"
  $requestedVersion = Get-HKCensusNodeVersion $AndroidRoot
  $nodeDir = Join-Path $toolRoot "node-v$requestedVersion-win-x64"
  $nodeExe = Join-Path $nodeDir "node.exe"
  $npmCmd = Join-Path $nodeDir "npm.cmd"
  $npxCmd = Join-Path $nodeDir "npx.cmd"

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

  return [PSCustomObject]@{
    Version = $requestedVersion
    Dir = $nodeDir
    Node = $nodeExe
    Npm = $npmCmd
    Npx = $npxCmd
  }
}

function Set-HKCensusToolchainEnvironment([string]$AndroidRoot) {
  $node = Initialize-HKCensusNodeToolchain $AndroidRoot
  $javaHome = Resolve-HKCensusJavaHome

  if ($javaHome) {
    $env:JAVA_HOME = $javaHome
    $env:Path = "$javaHome\bin;$($node.Dir);$env:Path"
    Write-Host "Using JAVA_HOME=$javaHome"
  } else {
    $env:Path = "$($node.Dir);$env:Path"
    Write-Warning "No supported JDK 17-21 was found. Android builds may fail until JAVA_HOME points to a supported JDK."
  }

  return $node
}

function Import-HKCensusProperties([string]$Path) {
  $properties = @{}
  if (-not (Test-Path $Path)) {
    return $properties
  }

  foreach ($line in Get-Content -LiteralPath $Path) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) {
      continue
    }
    $parts = $trimmed -split "=", 2
    if ($parts.Count -eq 2) {
      $properties[$parts[0].Trim()] = $parts[1].Trim()
    }
  }

  return $properties
}

function Get-HKCensusEnvValue([string]$Name) {
  $envPath = "Env:$Name"
  if (Test-Path $envPath) {
    return (Get-Item -Path $envPath).Value
  }
  return $null
}

function Resolve-HKCensusPath([string]$BasePath, [string]$Value) {
  if ([string]::IsNullOrWhiteSpace($Value)) {
    return $null
  }
  if ([System.IO.Path]::IsPathRooted($Value)) {
    return $Value
  }
  return (Join-Path $BasePath $Value)
}

function Set-HKCensusReleaseEnvironment(
  [string]$AndroidRoot,
  [hashtable]$Overrides = @{}
) {
  $releaseFile = Join-Path $AndroidRoot "release.properties"
  $properties = Import-HKCensusProperties $releaseFile

  $legacyAliases = @{
    KEYSTORE_FILE = "ANDROID_KEYSTORE_FILE"
    KEYSTORE_PASSWORD = "ANDROID_KEYSTORE_PASSWORD"
    KEY_ALIAS = "ANDROID_KEY_ALIAS"
    KEY_PASSWORD = "ANDROID_KEY_PASSWORD"
    DEBUG_KEYSTORE_FILE = "ANDROID_DEBUG_KEYSTORE_FILE"
    DEBUG_KEYSTORE_PASSWORD = "ANDROID_DEBUG_KEYSTORE_PASSWORD"
    DEBUG_KEY_ALIAS = "ANDROID_DEBUG_KEY_ALIAS"
    DEBUG_KEY_PASSWORD = "ANDROID_DEBUG_KEY_PASSWORD"
  }

  foreach ($key in $legacyAliases.Keys) {
    $canonicalName = "HKCENSUS_$key"
    $currentValue = Get-HKCensusEnvValue $canonicalName
    if (-not [string]::IsNullOrWhiteSpace($currentValue)) {
      continue
    }

    $legacyValue = Get-HKCensusEnvValue $legacyAliases[$key]
    if (-not [string]::IsNullOrWhiteSpace($legacyValue)) {
      Set-Item -Path "Env:$canonicalName" -Value $legacyValue
    }
  }

  foreach ($key in $properties.Keys) {
    if ([string]::IsNullOrWhiteSpace($properties[$key])) {
      continue
    }
    $canonicalName = "HKCENSUS_$key"
    $currentValue = Get-HKCensusEnvValue $canonicalName
    if ([string]::IsNullOrWhiteSpace($currentValue)) {
      Set-Item -Path "Env:$canonicalName" -Value $properties[$key]
    }
  }

  foreach ($key in $Overrides.Keys) {
    if ([string]::IsNullOrWhiteSpace($Overrides[$key])) {
      continue
    }
    Set-Item -Path "Env:HKCENSUS_$key" -Value $Overrides[$key]
  }

  return $releaseFile
}
