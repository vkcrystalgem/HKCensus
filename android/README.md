# HK Census Mobile App

This folder contains a React Native app for Android that mirrors the same ten analysis sections used in the local web report.

## Highlights

- Interactive historical charts rendered with `react-native-svg`
- Local bundled data generated from the repo's cached HK Census source files
- Android package configured as `com.vkcrystalgem.hkcensus`
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
```

Or from the repo root, regenerate the web report and bundled mobile data together:

```powershell
python build_report.py
```

## Notes

- The app uses local rendering and bundled data rather than embedding the web page.
- The current scaffold uses Expo React Native conventions to keep the Android app self-contained under this folder.
- If your machine already has a current Node 24 LTS runtime, you can use plain `npm install`, `npm test`, `npm run typecheck`, and `npm run android`.
- For Android builds, avoid Java 25. Gradle and the Android plugin currently expect JDK 17 to 21. The launcher script automatically selects Android Studio's bundled Java 21 when it is installed.
