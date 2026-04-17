# Android Variant Builds

This folder builds both Android variants for HK Census:

- release APK
- release AAB
- debug APK
- debug AAB

The intent is to keep the dual-keystore workflow in one place.

## Expected signing split

- Release:
  - Keystore: `C:\github\android-my-keystore\android-release.keystore`
  - Alias: `android_release`
  - SHA-256: `D5:0D:BB:B0:3E:97:3D:05:EB:7D:0F:5F:9E:8F:CE:D9:9D:24:E0:9B:0A:A4:36:18:A8:96:16:F2:86:36:56:E1`
- Debug:
  - Keystore: `C:\github\android-my-keystore\my-release-key.keystore`
  - Alias: `androiddebugkey`
  - SHA-256: `FA:C6:17:45:DC:09:03:78:6F:B9:ED:E6:2A:96:2B:39:9F:73:48:F0:BB:6F:89:9B:83:32:66:75:91:03:3B:9C`

## Build

From `C:\github\HKCensus\android`:

```powershell
$env:ANDROID_KEYSTORE_FILE='C:\github\android-my-keystore\android-release.keystore'
$env:ANDROID_KEYSTORE_PASSWORD='android'
$env:ANDROID_KEY_ALIAS='android_release'
$env:ANDROID_KEY_PASSWORD='android'
$env:ANDROID_DEBUG_KEYSTORE_FILE='C:\github\android-my-keystore\my-release-key.keystore'
$env:ANDROID_DEBUG_KEYSTORE_PASSWORD='android'
$env:ANDROID_DEBUG_KEY_ALIAS='androiddebugkey'
$env:ANDROID_DEBUG_KEY_PASSWORD='android'
powershell -ExecutionPolicy Bypass -File .\variant-builds\build-variants.ps1
```

The script writes:

- `variant-builds\out\hkcensus-release.apk`
- `variant-builds\out\hkcensus-release.aab`
- `variant-builds\out\hkcensus-debug.apk`
- `variant-builds\out\hkcensus-debug.aab`

## Notes

- The tracked Expo config remains the source of truth. The script runs `expo prebuild` first unless you pass `-SkipPrebuild`.
- Release signing uses the existing `ANDROID_*` variables.
- Debug signing uses `ANDROID_DEBUG_*` variables.
- If you prefer `HKCENSUS_*`, the script also accepts:
  - `HKCENSUS_KEYSTORE_FILE`, `HKCENSUS_KEYSTORE_PASSWORD`, `HKCENSUS_KEY_ALIAS`, `HKCENSUS_KEY_PASSWORD`
  - `HKCENSUS_DEBUG_KEYSTORE_FILE`, `HKCENSUS_DEBUG_KEYSTORE_PASSWORD`, `HKCENSUS_DEBUG_KEY_ALIAS`, `HKCENSUS_DEBUG_KEY_PASSWORD`
