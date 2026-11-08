import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import publish_play


class PlayEditCleanupChecks(unittest.TestCase):
    def setUp(self):
        self.service = MagicMock()
        self.service.edits().bundles().upload().execute.return_value = {"versionCode": 2}
        for target, value in (
            ("create_service", self.service),
            ("require_path", Path(__file__)),
            ("insert_edit", "temporary-edit"),
            ("list_tracks", []),
            ("MediaFileUpload", MagicMock()),
        ):
            mock_patch = patch.object(publish_play, target, return_value=value)
            mock_patch.start()
            self.addCleanup(mock_patch.stop)

    def run_main(self, *arguments):
        with patch.object(sys, "argv", ["publish_play.py", *arguments]), contextlib.redirect_stdout(io.StringIO()):
            return publish_play.main()

    def assert_edit_deleted(self):
        self.service.edits().delete.assert_called_once_with(
            packageName="com.vkcrystalgem.hkcensus", editId="temporary-edit"
        )

    def test_query_removes_temporary_edit(self):
        self.assertEqual(self.run_main("--query-next-version-code"), 0)
        self.assert_edit_deleted()
        self.service.edits().commit.assert_not_called()

    def test_failed_upload_removes_uncommitted_edit(self):
        self.service.edits().bundles().upload().execute.side_effect = RuntimeError("upload failed")
        with self.assertRaisesRegex(RuntimeError, "upload failed"):
            self.run_main()
        self.assert_edit_deleted()

    def test_failed_commit_removes_uncommitted_edit(self):
        self.service.edits().commit().execute.side_effect = RuntimeError("commit rejected")
        with self.assertRaisesRegex(RuntimeError, "commit rejected"):
            self.run_main()
        self.assert_edit_deleted()

    def test_successful_commit_is_preserved(self):
        self.assertEqual(self.run_main(), 0)
        self.service.edits().delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
