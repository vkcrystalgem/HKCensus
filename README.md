# HK Census Trend Report

This project fetches selected historical series from the Hong Kong Census and Statistics Department, computes ten trend views, and writes a local HTML report to `dist/index.html`.

The report is rendered locally with inline SVG charts. It does not depend on a remote charting library at runtime.

A React Native Android app lives under `android/` and uses the same ten-section analysis via a generated bundled data payload.

The Android app targets Node.js 24 LTS. A local bootstrap script is included under `android/scripts/` so the app can still be installed and tested on machines that still resolve an older global Node runtime. For Android builds it also prefers Android Studio's bundled Java 21 runtime, because Java 25 is too new for the current Gradle and Android plugin stack.

The tracked source of truth for Android SDK levels is [android/app.json](/c:/github/HKCensus/android/app.json). Expo SDK 54 and the `expo-build-properties` plugin pin Android `compileSdkVersion 36`, `targetSdkVersion 36`, and build tools `36.0.0`, so `expo prebuild` regenerates a Play-compatible native project instead of relying on hand edits under `android/android/`.

Android release packaging and local Google Play publishing are documented in [android/RELEASE.md](/c:/github/HKCensus/android/RELEASE.md).
The publication path is the [GitHub build and Play release workflow](android/GITHUB_RELEASE.md). It builds the committed app on GitHub, publishes to the selected Play track, and verifies the resulting release.
Local release automation remains available under [android/publish-automation/README.md](/c:/github/HKCensus/android/publish-automation/README.md).

The [HK Census privacy policy](https://vkcrystalgem.github.io/hkcensus_privacy_policy.html) is hosted on GitHub Pages. Its source is maintained in [docs/hkcensus_privacy_policy.html](docs/hkcensus_privacy_policy.html) and published as the same-named file in [vkcrystalgem.github.io](https://github.com/vkcrystalgem/vkcrystalgem.github.io). The app links to this page from its opening screen.
The [site root](https://vkcrystalgem.github.io/) displays the same policy using [docs/index.html](docs/index.html), so both addresses use one policy source.

## What it covers

- Population level
- Population growth components
- Ageing and dependency
- Fertility pressure
- Household downsizing
- Household income
- Labour force participation
- Unemployment cycle
- Real GDP per capita
- Inflation regime

## Run it

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Build or refresh the report:

```powershell
python build_report.py
```

That command now does two things:

- rebuilds the local web report in `dist/index.html`
- regenerates the Android app payload in `android/src/data/reportData.json`

## Test the Android app

From `C:\github\HKCensus\android`, use the local Node bootstrap if your global `node` is older than 24:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 install
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 test
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 typecheck
```

To launch the app on an emulator or a connected Android device:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-node.ps1 android
```

If your machine already has a modern Node 24 LTS install, the equivalent native commands are:

```powershell
npm install
npm test
npm run typecheck
npm run android
```

The generated report includes:

- one primary long-history chart for each section
- supporting mini graphics chosen for each section
- event markers such as the 2000 dot-com bubble, the 2003 SARS outbreak, the 2008 global financial crisis, and the 2020 COVID-19 shock where relevant to the time range

Check whether any configured source tables have newer `last_modified_date` values without rebuilding:

```powershell
python build_report.py --check-only
```

Force a full refresh of cached source files and rebuild:

```powershell
python build_report.py --force-refresh
```

Skip the Android payload regeneration if you only want the web report:

```powershell
python build_report.py --skip-mobile-export
```

## Update behavior

- Raw C&SD metadata and CSV files are cached under `data/raw/`.
- The last-seen source dates are recorded in `data/metadata.json`.
- Each run checks the configured tables for a newer official `last_modified_date`.
- If a table changed, the script refreshes the cache and rewrites `dist/index.html`.
- A normal build also refreshes the bundled mobile payload used by the React Native app.

## Periodic local checks

On Windows, schedule the report with Task Scheduler and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "cd C:\github\HKCensus; python build_report.py"
```

That gives you a local periodic check plus automatic incorporation of newly published values in the configured source set.

## Build a signed Android release

For a reusable local release flow, either keep signing values in `android/release.properties` or provide them through environment variables.

From `C:\github\HKCensus`:

```powershell
$env:ANDROID_KEYSTORE_FILE='C:\github\android-my-keystore\android-release.keystore'
$env:ANDROID_KEYSTORE_PASSWORD='android'
$env:ANDROID_KEY_ALIAS='android_release'
$env:ANDROID_KEY_PASSWORD='android'
powershell -ExecutionPolicy Bypass -File .\android\scripts\build-release.ps1 -VersionCode 2 -VersionName 1.0.1
```

That writes:

- `android\android\app\build\outputs\apk\release\app-release.apk`
- `android\android\app\build\outputs\bundle\release\app-release.aab`

Use the `.aab` for Google Play upload. Keep keystores, `android/release.properties`, and any Play service-account JSON local only.
