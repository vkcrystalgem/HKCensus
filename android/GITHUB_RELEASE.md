# Build and publish through GitHub

[Build and publish Google Play](../.github/workflows/publish-play.yml) tests the committed app, builds signed APK/AAB files on a GitHub-hosted Windows runner, uploads the new bundle to Play, and verifies its completed track status and SHA-256 checksum through a fresh Play API query.

The app uses Expo SDK 54 and targets Android 16 / API 36. The workflow reads the built APK manifest and checks the target SDK and release version before uploading the AAB.

The workflow releases the data already committed in `src/data/reportData.json`. Refresh data with `python build_report.py`, review the report, and commit both generated outputs before starting a release. It does not replace the data during a release build.

## Repository secrets

Configure these encrypted Actions secrets under the repository's **Settings → Secrets and variables → Actions**:

| Secret | Value |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | Base64 of the existing Play upload keystore |
| `ANDROID_KEYSTORE_PASSWORD` | Keystore password |
| `ANDROID_KEY_ALIAS` | `android_release` for the currently registered key |
| `ANDROID_KEY_PASSWORD` | Private-key password |
| `PLAY_SERVICE_ACCOUNT_JSON` | Complete Play service-account JSON |

The current registered upload certificate SHA-1 is `7E:DA:51:3A:97:1B:D1:2C:DA:78:9C:B2:5A:D2:BC:FC:DD:F3:26:81`. The workflow rejects a different signing certificate before building. The original local key is `C:\github\android-my-keystore\android-release.keystore`; the separately generated `android/keys/upload-keystore.jks` does not match Play.

Credentials are restored into the runner's temporary folder and removed after the job. They are not included in the repository or workflow artifacts. The service account needs permission to release this app to the selected Play track.

## Start a release

Open **Actions → Build and publish Google Play → Run workflow** and select:

- Branch containing the reviewed data and code.
- Track: `internal` is the default; `beta` and `production` are explicit alternatives.
- Version name: for example, `1.0.1`.
- Version code: leave blank to choose one higher than every uploaded bundle/APK and track version.

Using GitHub CLI:

```powershell
gh workflow run publish-play.yml --ref master -f track=internal -f version_name=1.0.1
gh run list --workflow publish-play.yml
gh run watch <run-id> --exit-status
```

Runs are serialized for this app to prevent simultaneous version selection and Play edits. A successful run means the release is `completed` on the selected track and the bundle in Play matches the GitHub-built AAB. A completed internal release is available to internal testers; public publication requires the production track and Play's applicable review process.

The workflow's artifact contains signed APK/AAB files, a release plan, upload receipt, final verification receipt, and release notes. The final receipt records the source commit and uploaded bundle checksum.
