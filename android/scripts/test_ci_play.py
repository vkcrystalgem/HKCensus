import unittest
from unittest.mock import MagicMock, patch

from ci_play import read_snapshot, select_version_code, uploaded_versions, verify_release


class PlayReleaseChecks(unittest.TestCase):
    def test_version_selection_includes_unassigned_uploaded_bundles(self):
        snapshot = {"tracks": [{"releases": [{"versionCodes": ["1"]}]}],
                    "bundles": [{"versionCode": 4}], "apks": [{"versionCode": 3}]}
        self.assertEqual(select_version_code(uploaded_versions(snapshot), ""), 5)
        with self.assertRaises(ValueError):
            select_version_code(uploaded_versions(snapshot), "4")

    def test_snapshot_edit_is_deleted_when_a_read_fails(self):
        service = MagicMock()
        service.edits().tracks().list().execute.side_effect = RuntimeError("read failed")
        with patch("ci_play.insert_edit", return_value="temporary-edit"):
            with self.assertRaises(RuntimeError):
                read_snapshot(service, "example.package")
        service.edits().delete.assert_called_once_with(
            packageName="example.package", editId="temporary-edit")

    def test_verification_requires_completed_status_and_matching_bundle(self):
        snapshot = {"tracks": [{"track": "internal", "releases": [
            {"versionCodes": ["2"], "status": "completed"}]}],
            "bundles": [{"versionCode": 2, "sha256": "abc"}], "apks": []}
        self.assertEqual(verify_release(snapshot, "internal", 2, "ABC")["status"], "completed")
        with self.assertRaises(ValueError):
            verify_release(snapshot, "internal", 2, "different")
        snapshot["tracks"][0]["releases"][0]["status"] = "draft"
        with self.assertRaises(ValueError):
            verify_release(snapshot, "internal", 2, "abc")


if __name__ == "__main__":
    unittest.main()
