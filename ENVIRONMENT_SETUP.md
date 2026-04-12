# HK Census Environment Setup Reference

This file summarizes the environment required to build, test, and run both the Python report generator and the React Native Android app in this repository.

All commands below assume Windows PowerShell and the workspace root at `C:\github\HKCensus`.

## Scope

- Local web report generation from Hong Kong C&SD data
- Mobile payload generation for the Android app
- React Native Android app build, test, and launch
- Known environment pitfalls that were already hit in this repo

## Required Software

### Python

- Python 3.x
- `pip`

Install Python dependencies from the repo root:

```powershell
python -m pip install -r requirements.txt
```

Used for:

- `build_report.py`
- `export_mobile_data.py`
- data refresh and report generation

### Node.js and npm

The Android app is pinned to Node 24 LTS.

Current repo expectation:

- Node `24.14.1`
- npm `11.x`

The repo already includes a bootstrap launcher:

- [android/scripts/use-node.ps1](/c:/github/HKCensus/android/scripts/use-node.ps1)

This script:

- downloads the pinned Node version from [android/.nvmrc](/c:/github/HKCensus/android/.nvmrc) into `android/.tooling/`
- uses that local Node instead of any stale system-wide Node
- avoids build failures caused by an old global Node install

You do not need to rely on a global Node installation if you use the script.

### Java

For Android builds, use JDK 17 to 21.

Working choice on this machine:

- Android Studio bundled JBR: `C:\Program Files\Android\Android Studio\jbr`
- detected Java version: `21`

Do not use Java 25 for this project.

The launcher script automatically prefers:

1. `HKCENSUS_JAVA_HOME` if you set it
2. Android Studio bundled JBR
3. a valid `JAVA_HOME` if it points to JDK 17 to 21
4. another installed JDK 17 to 21 under common Windows install paths

### Android Studio and Android SDK

Install Android Studio with:

- Android SDK
- Android SDK Platform for the target API used by the project
- Android SDK Build-Tools
- Android Emulator
- at least one Android Virtual Device

The app can also run on a physical Android device with USB debugging enabled.

Optional but useful:

- add `platform-tools` to `PATH` so `adb` is directly available in the shell

## Repo Configuration

### Root Python workflow

From the repo root:

```powershell
python build_report.py
```

This does two things:

- rebuilds the local report at `dist/index.html`
- regenerates the mobile payload at `android/src/data/reportData.json`

Other useful commands:

```powershell
python build_report.py --check-only
python build_report.py --force-refresh
python build_report.py --skip-mobile-export
```

### Android app workflow

From `C:\github\HKCensus\android`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 install
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 test
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 typecheck
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 android
```

Other useful commands:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 sync-data
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 start
```

If you are certain your global environment already matches the repo requirements, the equivalent native commands are:

```powershell
npm install
npm test
npm run typecheck
npm run android
```

Using the launcher script is safer.

## Current Pinned Mobile Stack

From [android/package.json](/c:/github/HKCensus/android/package.json):

- Expo `~52.0.0`
- `expo-asset` `~11.0.5`
- React `18.3.1`
- React Native `0.76.9`
- `react-native-svg` `15.8.0`
- TypeScript `^5.6.3`
- Jest `^29.7.0`
- `jest-expo` `~52.0.4`

Android package namespace:

- `com.vkcrystalgem.hkcensus`

## Verified Outputs

Successful Android debug builds produce:

- [app-debug.apk](/c:/github/HKCensus/android/android/app/build/outputs/apk/debug/app-debug.apk)

Verified checks:

- Jest unit tests passed
- TypeScript typecheck passed
- Android debug APK build completed

## Known Pitfalls and Resolutions

### 1. Old global Node version is picked up

Symptom:

- `node --version` shows an old release such as `12.13.1`
- Jest or TypeScript fail with syntax errors on modern JavaScript features

Cause:

- Windows shell resolves an outdated system `node.exe`

Resolution:

- use the local launcher script instead of raw `node` or `npm`
- the script downloads and uses the pinned Node 24 LTS toolchain from `android/.nvmrc`

Safe command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 install
```

### 2. Java 25 breaks the Android build

Symptom:

- Gradle fails with `Unsupported class file major version 69`

Cause:

- the Android Gradle toolchain used by this project is not compatible with Java 25

Resolution:

- build with JDK 17 to 21
- prefer Android Studio bundled Java 21
- use the launcher script so `JAVA_HOME` is set automatically

### 3. Expo Android build fails because Java and Node are mixed

Symptom:

- direct `gradlew` or `expo run:android` behaves inconsistently
- Gradle plugin resolution or autolinking fails

Cause:

- Gradle may use one Java runtime while Expo/Node-based autolinking uses another shell environment

Resolution:

- run Android builds through [android/scripts/use-node.ps1](/c:/github/HKCensus/android/scripts/use-node.ps1)
- this aligns both Node and Java for the same command session

### 4. Kotlin and Compose compiler mismatch

Symptom:

- build fails with Compose compiler requiring Kotlin `1.9.25` while another part resolves `1.9.24`

Cause:

- app was on `react-native 0.76.1` while Expo 52 expected a newer patch release

Resolution:

- update React Native to `0.76.9`
- keep Expo 52 compatible package versions aligned

### 5. Missing Expo package during Metro startup

Symptom:

- launch fails with `The required package expo-asset cannot be found`

Cause:

- Expo Metro config expects `expo-asset` as a direct dependency

Resolution:

- add `expo-asset` to [android/package.json](/c:/github/HKCensus/android/package.json)

### 6. `expo run:android` appears to hang after the build

Symptom:

- build succeeds
- command stays alive instead of exiting quickly

Cause:

- Expo may keep Metro running
- emulator or device deployment may still be in progress

How to verify:

- check for the debug APK under `android/android/app/build/outputs/apk/debug/`
- check whether the emulator is running
- check whether `adb` can see the device

This is not the same as a compile failure.

### 7. First native build creates Android native files

Symptom:

- `expo run:android` prints messages like `Created native directory` and `Finished prebuild`

Cause:

- Expo prebuild generates the native Android project under `android/android/`

Resolution:

- this is expected
- keep generated native files under version control only if that matches the repo policy

## Recommended Setup Order

1. Install Python and Python dependencies.
2. Install Android Studio with SDK and emulator support.
3. Open an emulator once to confirm the SDK is working.
4. From the repo root, run `python build_report.py`.
5. Change to `android/`.
6. Run `powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 install`.
7. Run `powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 test`.
8. Run `powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 typecheck`.
9. Run `powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 android`.

## Fast Troubleshooting Checklist

- If tests fail with JavaScript syntax support errors, you are probably using the wrong Node runtime.
- If Gradle mentions class file major version `69`, you are probably using Java 25.
- If Android build complains about Kotlin or Compose compatibility, verify the React Native version is `0.76.9`.
- If Metro complains about `expo-asset`, confirm it exists in [android/package.json](/c:/github/HKCensus/android/package.json) and reinstall packages.
- If `android` does not exit after building, check the emulator and Metro state before assuming the build failed.

## Reference Files

- [README.md](/c:/github/HKCensus/README.md)
- [android/README.md](/c:/github/HKCensus/android/README.md)
- [android/package.json](/c:/github/HKCensus/android/package.json)
- [android/.nvmrc](/c:/github/HKCensus/android/.nvmrc)
- [android/scripts/use-node.ps1](/c:/github/HKCensus/android/scripts/use-node.ps1)
- [build_report.py](/c:/github/HKCensus/build_report.py)
- [export_mobile_data.py](/c:/github/HKCensus/export_mobile_data.py)