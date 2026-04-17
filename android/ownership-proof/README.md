# Android Package Ownership Proof

This folder contains the local-only flow for Google's package ownership verification for `com.vkcrystalgem.hkcensus`.

It builds a signed release APK that contains `assets/adi-registration.properties` and is signed by the private key whose SHA-256 fingerprint matches Google's expected fingerprint.

## Expected certificate

- Package name: `com.vkcrystalgem.hkcensus`
- SHA-256: `FA:C6:17:45:DC:09:03:78:6F:B9:ED:E6:2A:96:2B:39:9F:73:48:F0:BB:6F:89:9B:83:32:66:75:91:03:3B:9C`

## Local files

- `adi-registration.properties`
  - local only
  - contains the Google ADI registration token
  - intentionally gitignored
- `out\hkcensus-ownership-proof.apk`
  - generated proof APK
  - intentionally gitignored

## Build

From `C:\github\HKCensus\android`:

```powershell
powershell -ExecutionPolicy Bypass -File .\ownership-proof\build-proof-apk.ps1
```

The script:

1. verifies the keystore fingerprint matches the Google-provided SHA-256
2. injects `adi-registration.properties` into the generated native Android assets during Expo prebuild
3. builds a signed release APK using the matching private key
4. copies the result to `ownership-proof\out\hkcensus-ownership-proof.apk`
5. verifies the APK contains `assets/adi-registration.properties`

## Default local keystore used by the script

- Keystore: `C:\github\android-my-keystore\my-release-key.keystore`
- Alias: `androiddebugkey`

These defaults can be overridden with script parameters if needed.
