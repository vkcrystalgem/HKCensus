import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


ANDROID_PUBLISHER_SCOPE = "https://www.googleapis.com/auth/androidpublisher"


def read_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def require_path(path_value: Optional[str], label: str) -> Path:
    if not path_value:
        raise SystemExit(f"Missing {label}.")
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists():
        raise SystemExit(f"{label} does not exist: {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload an HK Census Android App Bundle to Google Play.")
    parser.add_argument("--package-name", default=read_env("HKCENSUS_PACKAGE_NAME", "com.vkcrystalgem.hkcensus"))
    parser.add_argument("--track", default=read_env("HKCENSUS_PLAY_TRACK", "internal"))
    parser.add_argument("--release-status", default=read_env("HKCENSUS_PLAY_RELEASE_STATUS", "draft"))
    parser.add_argument("--release-name", default=read_env("HKCENSUS_PLAY_RELEASE_NAME"))
    parser.add_argument("--aab", default=read_env("HKCENSUS_AAB_PATH"))
    parser.add_argument("--service-account-json", default=read_env("HKCENSUS_PLAY_SERVICE_ACCOUNT_JSON"))
    parser.add_argument(
        "--changes-not-sent-for-review",
        action="store_true",
        default=read_env("HKCENSUS_PLAY_CHANGES_NOT_SENT_FOR_REVIEW", "false").lower() == "true",
    )
    args = parser.parse_args()

    aab_default = Path("android") / "app" / "build" / "outputs" / "bundle" / "release" / "app-release.aab"
    aab_path = require_path(args.aab or str(aab_default), "AAB file")
    service_account_path = require_path(args.service_account_json, "Play service account JSON")

    credentials = service_account.Credentials.from_service_account_file(
        service_account_path,
        scopes=[ANDROID_PUBLISHER_SCOPE],
    )

    service = build("androidpublisher", "v3", credentials=credentials, cache_discovery=False)
    edit = service.edits().insert(packageName=args.package_name, body={}).execute()
    edit_id = edit["id"]

    bundle_upload = service.edits().bundles().upload(
        packageName=args.package_name,
        editId=edit_id,
        media_body=MediaFileUpload(str(aab_path), mimetype="application/octet-stream"),
    ).execute()

    version_code = str(bundle_upload["versionCode"])
    release_body = {
        "releases": [
            {
                "name": args.release_name or f"{args.package_name} {version_code}",
                "versionCodes": [version_code],
                "status": args.release_status,
            }
        ]
    }

    service.edits().tracks().update(
        packageName=args.package_name,
        editId=edit_id,
        track=args.track,
        body=release_body,
    ).execute()

    service.edits().commit(
        packageName=args.package_name,
        editId=edit_id,
        changesNotSentForReview=args.changes_not_sent_for_review,
    ).execute()

    print(f"Uploaded {aab_path} to track '{args.track}' as versionCode {version_code}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
