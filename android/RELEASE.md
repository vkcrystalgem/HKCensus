# Android Release Guide

This guide prepares HK Census for Google Play release without committing any private keys or service-account files to Git.

For Google's package-name ownership verification flow, use the dedicated proof tooling in [ownership-proof/README.md](/c:/github/HKCensus/android/ownership-proof/README.md).

## What Gets Stored Locally Only

Keep these files out of version control:

- `android/release.properties`
- `android/keys/`
- `android/play/`
- any `*.jks` or `*.keystore`
- any Play service-account JSON file

The repo already ignores these paths.

## Release Artifact Types

- Use `app-release.apk` for local installation and final device checks.
- Use `app-release.aab` for Google Play upload.

For Google Play, the bundle is the important artifact.

## One-Time Setup

From `C:\github\HKCensus\android`:

1. Install app dependencies:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 install
```

2. Generate a local upload keystore and a local release properties file:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\new-upload-keystore.ps1
```

This creates:

- `android/keys/upload-keystore.jks`
- `android/release.properties`

Back up both files securely. If you lose the upload keystore after using it with Play App Signing, recovery is possible but operationally annoying.

3. If you plan to publish through the Play Developer API, install the Python packages:

```powershell
python -m pip install -r .\requirements-publish.txt
```

4. Put your Play service-account JSON in a local ignored folder, for example:

- `android/play/service-account.json`

Then set or update this line in `android/release.properties`:

```properties
PLAY_SERVICE_ACCOUNT_JSON=play/service-account.json
```

## Build Signed Release Artifacts

From `C:\github\HKCensus\android`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-release.ps1
```

If you prefer not to keep `android/release.properties`, you can provide signing values entirely through environment variables:

```powershell
$env:ANDROID_KEYSTORE_FILE='C:\github\android-my-keystore\android-release.keystore'
$env:ANDROID_KEYSTORE_PASSWORD='android'
$env:ANDROID_KEY_ALIAS='android_release'
$env:ANDROID_KEY_PASSWORD='android'
powershell -ExecutionPolicy Bypass -File .\scripts\build-release.ps1 -VersionCode 2 -VersionName 1.0.1
```

That builds:

- `android\app\build\outputs\apk\release\app-release.apk`
- `android\app\build\outputs\bundle\release\app-release.aab`

Useful variants:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-release.ps1 -BundleOnly
powershell -ExecutionPolicy Bypass -File .\scripts\build-release.ps1 -ApkOnly
powershell -ExecutionPolicy Bypass -File .\scripts\build-release.ps1 -VersionCode 2 -VersionName 1.0.1
```

## Publish To Google Play

The local publish script uploads the generated AAB to a Play track using a local service-account file.

From `C:\github\HKCensus\android`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish-play.ps1
```

Default values come from `android/release.properties`:

- `PLAY_TRACK=internal`
- `PLAY_RELEASE_STATUS=draft`
- `PLAY_RELEASE_NAME=HK Census 1.0.0`

You can override them at runtime:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish-play.ps1 -Track production -ReleaseStatus completed -ReleaseName "HK Census 1.0.1"
```

If the AAB has not been built yet:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish-play.ps1 -Build
```

## Recommended Release Sequence

1. Refresh the shared data payload:

```powershell
cd C:\github\HKCensus
python build_report.py
```

2. Run the mobile tests:

```powershell
cd C:\github\HKCensus\android
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 test
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 typecheck
```

3. Build the release APK and AAB:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-release.ps1
```

4. Install the APK locally and sanity-check the app.

5. Upload the AAB to the `internal` track first:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish-play.ps1 -Track internal -ReleaseStatus draft
```

6. Promote to a wider track only after validation in Play Console.

## Common Failure Modes

### Missing signing config

Symptom:

- `bundleRelease` or `assembleRelease` fails with a missing signing configuration message

Fix:

- either create `android/release.properties`
- or export `ANDROID_KEYSTORE_FILE`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, and `ANDROID_KEY_PASSWORD`
- or export the equivalent `HKCENSUS_*` names directly

### Wrong Java version

Symptom:

- Gradle fails on Java 25 related class or plugin issues

Fix:

- use `scripts/build-release.ps1` or `scripts/use-node.ps1`
- both prefer Android Studio's Java 21 runtime

### Bundle upload fails immediately

Symptom:

- Play upload script says the service-account JSON is missing

Fix:

- place the JSON file under `android/play/` or another local path
- point `PLAY_SERVICE_ACCOUNT_JSON` at that file in `android/release.properties`

### Google Play rejects the upload

Common causes:

- package name does not match the Play app
- version code is not higher than the last uploaded release
- target SDK in the generated native app is stale because `expo prebuild` was not rerun after config changes
- Play Console metadata or policy declarations are incomplete

## Relevant Files

- [app.json](/c:/github/HKCensus/android/app.json)
- [with-release-build.js](/c:/github/HKCensus/android/plugins/with-release-build.js)
- [release.properties.example](/c:/github/HKCensus/android/release.properties.example)
- [common.ps1](/c:/github/HKCensus/android/scripts/common.ps1)
- [new-upload-keystore.ps1](/c:/github/HKCensus/android/scripts/new-upload-keystore.ps1)
- [build-release.ps1](/c:/github/HKCensus/android/scripts/build-release.ps1)
- [publish-play.ps1](/c:/github/HKCensus/android/scripts/publish-play.ps1)
- [publish_play.py](/c:/github/HKCensus/android/scripts/publish_play.py)
