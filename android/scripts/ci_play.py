"""Plan and verify a GitHub-built Play release without changing Play tracks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from publish_play import create_service, extract_version_codes, insert_edit, require_path


PACKAGE_NAME = "com.vkcrystalgem.hkcensus"


def uploaded_versions(snapshot: dict[str, Any]) -> list[int]:
    versions = set(extract_version_codes(snapshot["tracks"]))
    for kind in ("bundles", "apks"):
        versions.update(int(item["versionCode"]) for item in snapshot[kind])
    return sorted(versions)


def select_version_code(existing: list[int], requested: str) -> int:
    highest = max(existing, default=0)
    if requested.strip():
        try:
            candidate = int(requested)
        except ValueError as exc:
            raise ValueError("Version code must be a positive integer.") from exc
    else:
        candidate = highest + 1
    if candidate <= highest or candidate > 2_100_000_000:
        raise ValueError(f"Version code must exceed {highest} and be at most 2100000000.")
    return candidate


def read_snapshot(service: Any, package: str) -> dict[str, Any]:
    edit_id = insert_edit(service, package)
    try:
        snapshot = {}
        for resource in ("tracks", "bundles", "apks"):
            response = getattr(service.edits(), resource)().list(
                packageName=package, editId=edit_id
            ).execute(num_retries=3)
            snapshot[resource] = response.get(resource, [])
        return snapshot
    finally:
        service.edits().delete(packageName=package, editId=edit_id).execute(num_retries=3)


def verify_release(snapshot: dict[str, Any], track: str, code: int, digest: str) -> dict[str, Any]:
    releases = [
        release
        for item in snapshot["tracks"] if item["track"] == track
        for release in item.get("releases", [])
        if str(code) in [str(value) for value in release.get("versionCodes", [])]
    ]
    if len(releases) != 1 or releases[0].get("status") != "completed":
        raise ValueError(f"Play does not show version {code} completed on {track}.")
    bundle = next((item for item in snapshot["bundles"] if int(item["versionCode"]) == code), None)
    if not bundle or bundle.get("sha256", "").lower() != digest.lower():
        raise ValueError("Play bundle checksum differs from the GitHub-built AAB.")
    return releases[0]


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "verify"))
    parser.add_argument("--track", choices=("internal", "beta", "production"), default="internal")
    parser.add_argument("--version-name", default=os.environ.get("RELEASE_VERSION_NAME", "1.0.1"))
    parser.add_argument("--version-code", default=os.environ.get("RELEASE_VERSION_CODE", ""))
    parser.add_argument("--aab", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("release-out"))
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", args.version_name):
        parser.error("Version name must be a semantic version such as 1.0.1.")
    credentials = require_path(os.environ.get("HKCENSUS_PLAY_SERVICE_ACCOUNT_JSON"), "Play credentials")
    snapshot = read_snapshot(create_service(credentials), PACKAGE_NAME)
    if args.mode == "plan":
        code = select_version_code(uploaded_versions(snapshot), args.version_code)
        write_json(args.out_dir / "play-before.json", snapshot)
        write_json(args.out_dir / "release-plan.json", {
            "packageName": PACKAGE_NAME, "track": args.track,
            "versionCode": code, "versionName": args.version_name,
            "sourceCommit": os.environ.get("GITHUB_SHA"),
        })
        output = os.environ.get("GITHUB_OUTPUT")
        if output:
            with open(output, "a", encoding="utf-8") as stream:
                stream.write(f"version_code={code}\nversion_name={args.version_name}\n")
        payload = json.loads(Path("android/src/data/reportData.json").read_text(encoding="utf-8"))
        (args.out_dir / "release-notes.en-US.txt").write_text(
            f"Updated Hong Kong Census and Statistics data through {payload['latest_release']}, "
            "including the latest available observations and historical revisions.", encoding="utf-8"
        )
        print(f"Release plan: HK Census {args.version_name} ({code}), track {args.track}.")
    else:
        if not args.aab or not args.version_code:
            parser.error("Verification requires --aab and --version-code.")
        code = int(args.version_code)
        digest = hashlib.sha256(args.aab.read_bytes()).hexdigest()
        release = verify_release(snapshot, args.track, code, digest)
        receipt = {
            "packageName": PACKAGE_NAME, "track": args.track,
            "versionCode": code, "versionName": args.version_name,
            "releaseName": release.get("name"), "status": release["status"],
            "sha256": digest, "sourceCommit": os.environ.get("GITHUB_SHA"),
            "verifiedAtUtc": datetime.now(timezone.utc).isoformat(),
        }
        write_json(args.out_dir / "play-verified.json", receipt)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as stream:
                stream.write(
                    f"Published **HK Census {args.version_name} ({code})** to **{args.track}**.\n\n"
                    f"Play status: **completed**. Uploaded AAB checksum verified: `{digest}`.\n"
                )
        print(f"Verified version {code}: completed on {args.track}; bundle checksum matches.")


if __name__ == "__main__":
    main()
