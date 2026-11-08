import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def resolve_optional_path(path_value: Optional[str]) -> Optional[Path]:
    if not path_value or not path_value.strip():
        return None
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def load_release_notes(path_value: Optional[str], language: str) -> Optional[List[Dict[str, str]]]:
    if not path_value:
        return None
    path = require_path(path_value, "Release notes file")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    return [{"language": language, "text": text}]


def create_service(service_account_path: Path) -> Any:
    credentials = service_account.Credentials.from_service_account_file(
        service_account_path,
        scopes=[ANDROID_PUBLISHER_SCOPE],
    )
    return build("androidpublisher", "v3", credentials=credentials, cache_discovery=False)


def insert_edit(service: Any, package_name: str) -> str:
    edit = service.edits().insert(packageName=package_name, body={}).execute()
    return edit["id"]


def list_tracks(service: Any, package_name: str, edit_id: str) -> List[Dict[str, Any]]:
    response = service.edits().tracks().list(packageName=package_name, editId=edit_id).execute()
    return list(response.get("tracks", []))


def extract_version_codes(tracks: List[Dict[str, Any]]) -> List[int]:
    version_codes: List[int] = []
    for track in tracks:
        for release in track.get("releases", []) or []:
            for version_code in release.get("versionCodes", []) or []:
                try:
                    version_codes.append(int(version_code))
                except (TypeError, ValueError):
                    continue
    return sorted(set(version_codes))


def build_track_snapshot(tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    snapshot: List[Dict[str, Any]] = []
    for track in tracks:
        releases = []
        for release in track.get("releases", []) or []:
            releases.append(
                {
                    "name": release.get("name"),
                    "status": release.get("status"),
                    "versionCodes": [str(code) for code in release.get("versionCodes", []) or []],
                }
            )
        snapshot.append({"track": track.get("track"), "releases": releases})
    return snapshot


def write_receipt(path_value: Optional[str], payload: Dict[str, Any]) -> None:
    output_path = resolve_optional_path(path_value)
    if output_path is None:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_query_receipt(
    package_name: str,
    track_snapshot: List[Dict[str, Any]],
    version_codes: List[int],
) -> Dict[str, Any]:
    current_max = max(version_codes) if version_codes else None
    next_code = current_max + 1 if current_max is not None else 1
    return {
        "packageName": package_name,
        "mode": "query-next-version-code",
        "existingVersionCodes": version_codes,
        "currentMaxVersionCode": current_max,
        "nextVersionCode": next_code,
        "tracks": track_snapshot,
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
    }


def build_upload_receipt(
    package_name: str,
    aab_path: Path,
    track: str,
    release_status: str,
    release_name: str,
    uploaded_version_code: int,
    existing_version_codes: List[int],
    changes_not_sent_for_review: bool,
    release_notes_file: Optional[str],
    release_notes_language: str,
) -> Dict[str, Any]:
    current_max = max(existing_version_codes) if existing_version_codes else None
    return {
        "packageName": package_name,
        "mode": "upload-bundle",
        "aabPath": str(aab_path),
        "track": track,
        "releaseStatus": release_status,
        "releaseName": release_name,
        "uploadedVersionCode": uploaded_version_code,
        "existingVersionCodesBeforeUpload": existing_version_codes,
        "currentMaxVersionCodeBeforeUpload": current_max,
        "changesNotSentForReview": changes_not_sent_for_review,
        "releaseNotesFile": release_notes_file,
        "releaseNotesLanguage": release_notes_language if release_notes_file else None,
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Query or publish HK Census Android releases through Google Play.")
    parser.add_argument("--package-name", default=read_env("HKCENSUS_PACKAGE_NAME", "com.vkcrystalgem.hkcensus"))
    parser.add_argument("--track", default=read_env("HKCENSUS_PLAY_TRACK", "internal"))
    parser.add_argument("--release-status", default=read_env("HKCENSUS_PLAY_RELEASE_STATUS", "completed"))
    parser.add_argument("--release-name", default=read_env("HKCENSUS_PLAY_RELEASE_NAME"))
    parser.add_argument("--aab", default=read_env("HKCENSUS_AAB_PATH"))
    parser.add_argument("--service-account-json", default=read_env("HKCENSUS_PLAY_SERVICE_ACCOUNT_JSON"))
    parser.add_argument("--release-notes-file", default=read_env("HKCENSUS_PLAY_RELEASE_NOTES_FILE"))
    parser.add_argument("--release-notes-language", default=read_env("HKCENSUS_PLAY_RELEASE_NOTES_LANGUAGE", "en-US"))
    parser.add_argument("--receipt-json", default=read_env("HKCENSUS_PLAY_RECEIPT_JSON"))
    parser.add_argument(
        "--changes-not-sent-for-review",
        action="store_true",
        default=read_env("HKCENSUS_PLAY_CHANGES_NOT_SENT_FOR_REVIEW", "false").lower() == "true",
    )
    parser.add_argument("--query-next-version-code", action="store_true")
    args = parser.parse_args()

    service_account_path = require_path(args.service_account_json, "Play service account JSON")
    service = create_service(service_account_path)
    edit_id = insert_edit(service, args.package_name)

    committed = False
    try:
        tracks = list_tracks(service, args.package_name, edit_id)
        track_snapshot = build_track_snapshot(tracks)
        existing_version_codes = extract_version_codes(tracks)

        if args.query_next_version_code:
            receipt = build_query_receipt(args.package_name, track_snapshot, existing_version_codes)
            write_receipt(args.receipt_json, receipt)
            print(receipt["nextVersionCode"])
            return 0

        aab_default = Path("android") / "app" / "build" / "outputs" / "bundle" / "release" / "app-release.aab"
        aab_path = require_path(args.aab or str(aab_default), "AAB file")
        release_notes = load_release_notes(args.release_notes_file, args.release_notes_language)

        bundle_upload = service.edits().bundles().upload(
            packageName=args.package_name,
            editId=edit_id,
            media_body=MediaFileUpload(str(aab_path), mimetype="application/octet-stream"),
        ).execute()

        uploaded_version_code = int(bundle_upload["versionCode"])
        resolved_release_name = args.release_name or f"{args.package_name} {uploaded_version_code}"
        release_definition: Dict[str, Any] = {
            "name": resolved_release_name,
            "versionCodes": [str(uploaded_version_code)],
            "status": args.release_status,
        }
        if release_notes:
            release_definition["releaseNotes"] = release_notes

        service.edits().tracks().update(
            packageName=args.package_name,
            editId=edit_id,
            track=args.track,
            body={"releases": [release_definition]},
        ).execute()

        service.edits().commit(
            packageName=args.package_name,
            editId=edit_id,
            changesNotSentForReview=args.changes_not_sent_for_review,
        ).execute()
        committed = True

        receipt = build_upload_receipt(
            package_name=args.package_name,
            aab_path=aab_path,
            track=args.track,
            release_status=args.release_status,
            release_name=resolved_release_name,
            uploaded_version_code=uploaded_version_code,
            existing_version_codes=existing_version_codes,
            changes_not_sent_for_review=args.changes_not_sent_for_review,
            release_notes_file=str(resolve_optional_path(args.release_notes_file)) if args.release_notes_file else None,
            release_notes_language=args.release_notes_language,
        )
        write_receipt(args.receipt_json, receipt)

        print(
            f"Uploaded {aab_path} to track '{args.track}' as versionCode {uploaded_version_code} "
            f"with status '{args.release_status}'."
        )
        return 0
    finally:
        if not committed:
            try:
                service.edits().delete(packageName=args.package_name, editId=edit_id).execute()
            except Exception as cleanup_error:
                print(f"Warning: could not remove the uncommitted Play edit ({type(cleanup_error).__name__}).", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
