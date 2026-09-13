import importlib.util
import os
import tempfile
import unittest
import zipfile
from pathlib import Path


class HelperTest(unittest.TestCase):
    def load_helper(self, directory):
        previous = os.environ.get("APPDATA")
        os.environ["APPDATA"] = directory
        try:
            spec = importlib.util.spec_from_file_location("helper", "helper/tboi_sync_helper.py")
            helper = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(helper)
            return helper
        finally:
            if previous is None:
                os.environ.pop("APPDATA", None)
            else:
                os.environ["APPDATA"] = previous

    def test_validation_and_atomic_state(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = self.load_helper(directory)
            data = {
                "achievements": [1, 2],
                "collectedItems": [],
                "completedChallenges": [],
                "completionMarks": {},
            }
            self.assertEqual(helper.validate_progress(data), data)
            with self.assertRaises(ValueError):
                helper.validate_progress({"achievements": []})
            with self.assertRaises(ValueError):
                helper.validate_progress({**data, "achievements": [True]})
            path = Path(directory) / "state.json"
            helper.write_json(path, data)
            self.assertEqual(helper.read_json(path), data)
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_dependency_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = self.load_helper(directory)
            game = Path(directory) / "game"
            game.mkdir()
            (game / "isaac-ng.exe").write_bytes(b"x")
            self.assertEqual(helper.game_edition(game), "repentance")
            (game / "dsound.dll").write_bytes(b"x")
            (game / "zhlREPENTOGON.dll").write_bytes(b"x")
            (game / "resources-repentogon").mkdir()
            self.assertTrue(helper.legacy_repentogon_installed(game))
            (game / "resources-dlc3").mkdir()
            self.assertEqual(helper.game_edition(game), "repentance_plus")
            (game / "Repentogon").mkdir()
            (game / "Repentogon" / "version.txt").write_text("1", encoding="utf-8")
            self.assertTrue(helper.plus_repentogon_installed(game))

    def test_safe_zip_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = self.load_helper(directory)
            archive_path = Path(directory) / "bad.zip"
            destination = Path(directory) / "dest"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../evil.txt", "no")
            with self.assertRaises(RuntimeError):
                helper.extract_zip_safely(archive_path, destination)

    def test_hash_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = self.load_helper(directory)
            value = "a" * 64
            self.assertEqual(helper.parse_sha256("sha256:" + value), value)
            with self.assertRaises(RuntimeError):
                helper.parse_sha256("bad")


if __name__ == "__main__":
    unittest.main()
