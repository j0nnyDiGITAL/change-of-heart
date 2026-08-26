import io, os, sys, zipfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.environment import create_memory_backup_zip, create_timestamped_backup, list_backups

class TestBackupZipGeneration(unittest.TestCase):
    def test_create_memory_backup_zip(self):
        raw_data = b"DATA_MAGIC_TEST_BYTES_P5R"
        zip_bytes = create_memory_backup_zip(raw_data, "DATA.DAT")
        self.assertIsInstance(zip_bytes, bytes)
        self.assertGreater(len(zip_bytes), 0)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
            self.assertIn("DATA.DAT", z.namelist())
            self.assertEqual(z.read("DATA+DAT".replace("+", ".")), raw_data)

    def test_local_disk_backup_created(self):
        tmp_dir = ROOT / "tests" / "fixtures" / "tmp_backup_test"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        save_file = tmp_dir / "DATA.DAT"
        save_file.write_bytes(b"CANONICAL_TEST_SAVE_CONTENT")
        try:
            zip_path = create_timestamped_backup(save_file)
            self.assertTrue(zip_path.exists())
            self.assertTrue(zip_path.name.endswith(".zip"))
            with zipfile.ZipFile(zip_path, "r") as z:
                self.assertIn("DATA.DAT", z.namelist())
                self.assertEqual(z.read("DATA.DAT"), b"CANONICAL_TEST_SAVE_CONTENT")
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
