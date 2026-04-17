# HK Census Mobile App

This folder contains a React Native app for Android that mirrors the same ten analysis sections used in the local web report.

For Android release packaging and Google Play publishing, see [RELEASE.md](/c:/github/HKCensus/android/RELEASE.md).
For Google's package ownership verification APK flow, see [ownership-proof/README.md](/c:/github/HKCensus/android/ownership-proof/README.md).
For building both debug and release APK/AAB variants with separate keys, see [variant-builds/README.md](/c:/github/HKCensus/android/variant-builds/README.md).
For local-only automated Google Play publishing, see [publish-automation/README.md](/c:/github/HKCensus/android/publish-automation/README.md).

## Highlights

- Interactive historical charts rendered with `react-native-svg`
- Local bundled data generated from the repo's cached HK Census source files
- Android package configured as `com.vkcrystalgem.hkcensus`
- Android SDK and build tools pinned in `app.json` through `expo-build-properties`, so `expo prebuild` keeps the generated native project at API 35
- Jest unit tests for chart math and payload structure
- Local Node.js 24 LTS bootstrap script for machines that still resolve an older global Node runtime or an unsupported Java runtime

## Expected workflow

1. Ensure Node.js 24 LTS is available, either globally or via the included bootstrap script. The script also prefers Android Studio's bundled Java 21 runtime for Gradle builds.
2. Install dependencies in this folder.
3. Regenerate `src/data/reportData.json` when the web analysis changes.
4. Run the app on an Android emulator or device.
5. Run the unit tests before shipping changes.

## Common commands

From `C:\github\HKCensus\android`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 install
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 sync-data
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 test
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 typecheck
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 android
powershell -ExecutionPolicy Bypass -File .\scripts\new-upload-keystore.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build-release.ps1
python -m pip install -r .\requirements-publish.txt
powershell -ExecutionPolicy Bypass -File .\scripts\publish-play.ps1
powershell -ExecutionPolicy Bypass -File .\publish-automation\publish-new-release.ps1 -DryRun
```

Or from the repo root, regenerate the web report and bundled mobile data together:

```powershell
python build_report.py
```

## Notes

- The app uses local rendering and bundled data rather than embedding the web page.
- The current scaffold uses Expo React Native conventions to keep the Android app self-contained under this folder.
- The tracked source of truth for Android SDK levels is `app.json`, not the generated `android/build.gradle`.
- If your machine already has a current Node 24 LTS runtime, you can use plain `npm install`, `npm test`, `npm run typecheck`, and `npm run android`.
- For Android builds, avoid Java 25. Gradle and the Android plugin currently expect JDK 17 to 21. The launcher script automatically selects Android Studio's bundled Java 21 when it is installed.
- Keep `release.properties`, keystores, and Play service-account JSON files local only. They are intentionally gitignored.
- The recommended Play publishing path is the local automation script under `publish-automation/`, not GitHub Actions, so secrets do not have to be stored on GitHub. The automation now defaults to publishing a `completed` release on whatever `PLAY_TRACK` you configure locally.

## Release from environment variables

If you do not want a local `release.properties` file, the release build also accepts these environment variables directly:

```powershell
$env:ANDROID_KEYSTORE_FILE='C:\github\android-my-keystore\android-release.keystore'
$env:ANDROID_KEYSTORE_PASSWORD='android'
$env:ANDROID_KEY_ALIAS='android_release'
$env:ANDROID_KEY_PASSWORD='android'
powershell -ExecutionPolicy Bypass -File .\scripts\build-release.ps1 -VersionCode 2 -VersionName 1.0.1
```

That produces:

- `android\app\build\outputs\apk\release\app-release.apk`
- `android\app\build\outputs\bundle\release\app-release.aab`
