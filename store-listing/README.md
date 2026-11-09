# HK Census Google Play listing packet

Prepared English (United States), `en-US`, listing materials for `com.vkcrystalgem.hkcensus`. These files do not change Play Console, upload an APK/AAB, send changes for review, or publish the app.

## Field and file mapping

| Play Console field | File or folder | Packet checks |
| --- | --- | --- |
| App name | `en-US/app-name.txt` | Nonempty, one line, at most 30 characters |
| Short description | `en-US/short-description.txt` | Nonempty, one line, at most 80 characters |
| Full description | `en-US/full-description.txt` | Nonempty, at most 4,000 characters |
| App icon | `graphics/app-icon-512.png` | 512 × 512, 32-bit RGBA PNG, all alpha 255, sRGB profile, at most 1 MiB |
| Feature graphic | `graphics/feature-graphic-1024x500.png` | 1024 × 500, 24-bit RGB PNG, sRGB profile, at most 15 MiB |
| Phone screenshots | `screenshots/phone/*.png` | 4–8 actual native 9:16 captures; both sides 1,080–3,840 px |
| 7-inch tablet screenshots | `screenshots/tablet-7inch/*.png` | 4–8 actual native 9:16 captures; both sides 320–3,840 px |
| 10-inch tablet screenshots | `screenshots/tablet-10inch/*.png` | 4–8 actual native 9:16 captures; both sides 1,080–7,680 px |

The completed set contains six 1,080 × 1,920 phone images, four 1,080 × 1,920 7-inch tablet images, and four 1,440 × 2,560 10-inch tablet images. All are opaque 24-bit RGB PNGs below 8 MiB, captured at native resolution from the real GitHub-built app on separate Android emulator profiles. Numeric filename prefixes set display order within each folder. Replacement captures must come from the corresponding device layout; increasing a phone image's dimensions does not make it a tablet screenshot.

The validator uses the stated preparation targets, including at least four captures per device group; this is stricter than Play's baseline screenshot count. See [Google's preview asset requirements](https://support.google.com/googleplay/android-developer/answer/9866151) for the current platform rules.

Use `en-US/UPLOAD_GUIDE.md` for paste/upload instructions and `en-US/alt-text-suggestions.md` for factual descriptions of the final images. Keep the default listing's preview video, desktop and Android XR fields empty: this packet supplies no matching assets for those fields. The privacy-policy URL is [the specific HK Census policy page](https://vkcrystalgem.github.io/hkcensus_privacy_policy.html).

## Validate and package

Requires Python 3.10 or later and Pillow (`python -m pip install Pillow`). From the repository root:

```powershell
python store-listing/package_listing.py --check-only
python store-listing/package_listing.py
```

The first command validates without writing anything. The second writes `store-listing/manifest.json` and `store-listing/HKCensus-GooglePlay-en-US.zip` only after validation passes. Missing captures, wrong modes, incorrect ratios, out-of-range dimensions and oversized files produce an explicit error and a nonzero exit code. No placeholders or synthetic screenshots are generated.

The ZIP contains only the three text files, two finished listing graphics, actual screenshot PNGs, upload guide, suggested alt text, this README and the generated manifest. It excludes source SVGs, renderers, QA previews, the adaptive foreground, raw captures, APK/AAB files, credentials, signing keys and the ZIP itself. To include the separate artwork attribution document, use `--include-sources`. An alternative destination can be selected with `--output path/to/packet.zip`.

`manifest.json` maps each asset to its Play field and records file size, SHA-256 hash, text lengths, image dimensions/mode and screenshot display order/counts. The supplied `provenance.json` is embedded as `captureProvenance`: it identifies the review APK's source commit, version 1.0.1 (code 3), successful GitHub build-only run, device profiles and original capture/export hashes. Both the APK/AAB hashes and every raw/exported screenshot's decoded RGB pixels were independently checked. The review build was not uploaded to Play. File specifications alone cannot verify that an image came from the real app.

ZIP entries are sorted with fixed timestamps and permissions, making repeated packaging reproducible when the source bytes, provenance and compression runtime are unchanged. The archive is a convenient handoff packet; Play Console requires the individual assets to be entered in their matching fields.

## Lossless capture format export

Android emulator captures can be RGBA PNGs even when every alpha value is 255. Play screenshot fields use JPEG or 24-bit PNG. This helper removes only a fully opaque alpha channel and verifies every decoded RGB pixel against the original; it never crops, resizes, composites, overlays or fabricates app UI:

```powershell
python store-listing/package_listing.py --export-capture path/to/raw-capture.png store-listing/screenshots/phone/01-overview.png
```

The raw file is preserved. Exports with transparency are rejected. An existing destination is rejected unless `--overwrite` is explicitly supplied. The helper prints the raw/exported SHA-256 hashes, dimensions, colour modes and the verified `rgbPixelsIdentical` result for the provenance record. Use this export separately from packet validation; capture authenticity still depends on the source APK and device evidence.
