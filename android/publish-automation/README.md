# Google Play Publish Automation

The preferred release path builds and publishes through [GitHub Actions](../GITHUB_RELEASE.md), using encrypted repository secrets. This folder provides a local fallback that builds and uploads from the current machine.

It is based on the same practical sequence used in the local `FlappyBirdClone` deploy flow:

1. resolve signing and Play credentials
2. build a signed release AAB
3. upload to a Play track

This local fallback reads credentials from the local environment or ignored configuration files and adds automatic version-code selection from Play.

## Local fallback files excluded from Git

- `android/release.properties`
- `android/play/service-account.json`
- any `*.jks` or `*.keystore`
- any environment variables that contain passwords
- generated publish receipts under `publish-automation/out/`

## Default behavior

`publish-new-release.ps1` will:

1. query Google Play for the current highest uploaded version code
2. choose the next safe version code automatically
3. reuse the app version from `app.json` as the Android `versionName` unless you override it
4. run Jest and TypeScript checks unless you skip them
5. build a signed release AAB
6. upload it to the configured Play track
7. write a local JSON receipt under `publish-automation/out/`

## Required local setup

- release signing credentials:
  - `ANDROID_KEYSTORE_FILE`
  - `ANDROID_KEYSTORE_PASSWORD`
  - `ANDROID_KEY_ALIAS`
  - `ANDROID_KEY_PASSWORD`
- Play API credential:
  - `PLAY_SERVICE_ACCOUNT_JSON` in `android/release.properties`
  - or `HKCENSUS_PLAY_SERVICE_ACCOUNT_JSON`

The release keystore and service-account JSON must stay outside Git.

## Example

From `C:\github\HKCensus\android`:

```powershell
$env:ANDROID_KEYSTORE_FILE='C:\github\android-my-keystore\android-release.keystore'
$env:ANDROID_KEYSTORE_PASSWORD='android'
$env:ANDROID_KEY_ALIAS='android_release'
$env:ANDROID_KEY_PASSWORD='android'
powershell -ExecutionPolicy Bypass -File .\publish-automation\publish-new-release.ps1
```

That uses the defaults from `android/release.properties` for:

- `PLAY_SERVICE_ACCOUNT_JSON`
- `PLAY_TRACK`
- `PLAY_RELEASE_STATUS`

If you leave `PLAY_RELEASE_STATUS` unset, the automation defaults to `completed` instead of `draft`. Set `PLAY_TRACK` in your local config to whichever track you want future releases to use by default.

## Useful options

```powershell
powershell -ExecutionPolicy Bypass -File .\publish-automation\publish-new-release.ps1 -DryRun
powershell -ExecutionPolicy Bypass -File .\publish-automation\publish-new-release.ps1 -Track production -ReleaseStatus completed
powershell -ExecutionPolicy Bypass -File .\publish-automation\publish-new-release.ps1 -VersionCode 12 -VersionName 1.0.12
powershell -ExecutionPolicy Bypass -File .\publish-automation\publish-new-release.ps1 -ReleaseNotesFile .\publish-automation\release-notes.en-US.example.txt
```

## Outputs

- uploaded AAB:
  - `android\app\build\outputs\bundle\release\app-release.aab`
- local receipt:
  - `publish-automation\out\play-release-<versionCode>.json`
- local version query receipt:
  - `publish-automation\out\next-version-code.json`
