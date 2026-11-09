# HK Census default store listing

Prepared for English (United States), `en-US`, on 9 November 2026. This packet prepares the listing; no Play Console changes are made by these files.

## Text fields

In Play Console, open **Grow users → Store presence → Store listings**, then edit the default English (United States) listing. Paste the contents of each text file without its filename:

| Play Console field | Prepared file | Google's limit |
| --- | --- | --- |
| App name | `app-name.txt` | 30 characters |
| Short description | `short-description.txt` | 80 characters |
| Full description | `full-description.txt` | 4,000 characters |

The copy describes the installed app's ten themes, touch-enabled charts, bundled offline statistics and official source links. It includes a visible independence statement and all nine source-table URLs. Retain that statement and source attribution when editing. Google requires clear sources and a clear statement of non-representation for independent apps that communicate government information. [Government information requirements](https://support.google.com/googleplay/android-developer/answer/9514050?hl=en)

The name and descriptions avoid ranking, pricing and promotional claims. The full description explains that the data updates through app releases, so it does not imply a live statistics feed. [Store listing text guidance](https://support.google.com/googleplay/android-developer/answer/13393723?hl=en)

## Graphics fields

Use the following finished asset sets, in their numbered display order:

| Field | Prepared target | Upload format |
| --- | --- | --- |
| App icon | `../graphics/app-icon-512.png`, 512 × 512 | 32-bit PNG, up to 1,024 KB |
| Feature graphic | `../graphics/feature-graphic-1024x500.png`, 1,024 × 500 | JPEG or 24-bit PNG without alpha |
| Phone screenshots | Six captures in `../screenshots/phone/`, 1,080 × 1,920 | 24-bit RGB PNG |
| 7-inch tablet screenshots | Four captures in `../screenshots/tablet-7inch/`, 1,080 × 1,920 | 24-bit RGB PNG |
| 10-inch tablet screenshots | Four captures in `../screenshots/tablet-10inch/`, 1,440 × 2,560 | 24-bit RGB PNG |

The original store icon and matching launcher artwork are configured in the app source used for the review build. The existing Play release is not changed by this preparation.

Screenshot APK provenance:

| Item | Review build |
| --- | --- |
| App version | 1.0.1 |
| Android version code | 3 |
| Target Android API | 36 |
| Build source | GitHub Actions with `publish_to_play=false` |
| GitHub build | [Successful build-only run 42625483879](https://github.com/vkcrystalgem/HKCensus/actions/runs/42625483879) |
| Source commit | `76e317610a874694cc31eaa86330c460bdbac829` |
| Play upload or publication | None for this review build (`uploaded=false`) |

The new captures show that APK's revised overview, privacy-policy link and readable chart annotations. They replace the older version-code-2 captures. The images are genuine native-resolution captures from temporary Android emulators; export only removes fully opaque alpha, without cropping, resizing or adding overlays. Android's status-bar demo mode supplies the consistent clock, battery and notification state. This build-only run and these materials do not upload a new Play release or change the store listing. Use the images with the reviewed app version they depict.

Google's baseline is at least two screenshots across device types; four phone captures at the target above also satisfy its stated resolution/count guidance for screenshot-based recommendation formats. Screenshots must show the actual app, and should not be stretched or presented as fabricated functionality. Up to eight screenshots can be provided per device type. [Preview asset requirements](https://support.google.com/googleplay/android-developer/answer/9866151?hl=en)

Use short, factual alt text for the actual content of each finished asset, within 140 characters. For tablet fields, use genuine tablet captures if supplied, not enlarged phone images. For Chromebook/tablet presentation Google specifies at least four captures, 1,080–7,680 px, with 9:16 portrait or 16:9 landscape proportions. [Device-specific screenshot guidance](https://support.google.com/googleplay/android-developer/answer/9866151?hl=en)

See `alt-text-suggestions.md` for descriptions matching the six phone, four 7-inch and four 10-inch views. Review the final images and adjust alt text if an image is replaced.

Leave preview video, desktop-specific and Android XR fields blank unless a genuine matching asset and supported experience are available. A standard preview video is optional and uses a YouTube video URL. [Video guidance](https://support.google.com/googleplay/android-developer/answer/9866151?hl=en)

## Privacy and contact

Use this exact privacy-policy URL in the app's privacy-policy field:

https://vkcrystalgem.github.io/hkcensus_privacy_policy.html

Use the project issue page as the support website:

https://github.com/vkcrystalgem/HKCensus/issues

Keep the developer's monitored support email in the required contact-email field; an email address has not been invented for this packet. The GitHub support URL does not replace that required email. [App setup and contact details](https://support.google.com/googleplay/android-developer/answer/9859152?hl=en)

## Review before saving

Native visual QA also found overflow in the small supporting charts on narrow phones. The selected phone screenshots show intact main charts. Resolve that app layout issue before a production rollout; details are recorded in the repository's `android/KNOWN_ISSUES.md`.

Confirm the copy and screenshots match the current release, keep the independence statement and official source links visible, and check the preview for cropped graphics. Saving a listing and sending changes for review are separate Play Console actions; the prepared packet does not publish the listing.
