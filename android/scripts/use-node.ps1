param(
  [Parameter(Position = 0)]
  [ValidateSet("node", "npm", "npx", "install", "test", "typecheck", "android", "ios", "start", "sync-data", "prebuild-android")]
  [string]$Command = "node",

  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$androidRoot = Split-Path -Parent $scriptDir
$commonPath = Join-Path $scriptDir "common.ps1"
. $commonPath
$node = Set-HKCensusToolchainEnvironment $androidRoot

Push-Location $androidRoot
try {
  switch ($Command) {
    'node' {
      & $node.Node @Args
    }
    'npm' {
      & $node.Npm @Args
    }
    'npx' {
      & $node.Npx @Args
    }
    'install' {
      & $node.Npm 'install' @Args
    }
    'test' {
      & $node.Npm 'test' @Args
    }
    'typecheck' {
      & $node.Npm 'run' 'typecheck' @Args
    }
    'android' {
      & $node.Npm 'run' 'android' @Args
    }
    'ios' {
      & $node.Npm 'run' 'ios' @Args
    }
    'start' {
      & $node.Npm 'start' @Args
    }
    'sync-data' {
      & $node.Npm 'run' 'sync-data' @Args
    }
    'prebuild-android' {
      & $node.Npx 'expo' 'prebuild' '--platform' 'android' '--no-install' @Args
    }
  }
} finally {
  Pop-Location
}

exit $LASTEXITCODE
