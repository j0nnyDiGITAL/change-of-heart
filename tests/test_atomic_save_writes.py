"""
Unit tests for two-phase atomic save write engine, fault injection, and rollback.
"""

import os
import tempfile
import unittest
from pathlib import Path

from core.atomic_writer import (
    ConcurrencyConflictError,
    SaveValidationError,
    atomic_restore_backup,
    atomic_write_save,
    compute_sha256,
    verify_save_bytes,
)
from core.crypto import SaveContainer
from core.editor import SaveEditor


class TestAtomicSaveWrites(unittest.TestCase):

    def setUp(self):
        self.fixture_path = Path("tests/fixtures/canonical_save.dat")
        self.assertTrue(self.fixture_path.exists(), "Canonical save fixture required")
        self.canonical_bytes = self.fixture_path.read_bytes()
        self.canonical_sha = compute_sha256(self.canonical_bytes)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.target_save = Path(self.temp_dir.name) / "DATA01" / "DATA.DAT"
        self.target_save.parent.mkdir(parents=True, exist_ok=True)
        self.target_save.write_bytes(self.canonical_bytes)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_verify_save_bytes_success(self):
        """Valid canonical save passes verification."""
        info = verify_save_bytes(self.canonical_bytes, strict_crc=True)
        self.assertTrue(info["valid"])
        self.assertTrue(info["file_crc_ok"])
        self.assertTrue(info["inner_crc_ok"])
        self.assertEqual(info["sha256"], self.canonical_sha)

    def test_verify_save_bytes_rejects_truncated(self):
        """Truncated bytes (< 0x34) are rejected immediately."""
        with self.assertRaises(SaveValidationError):
            verify_save_bytes(b"DATA\x00\x00")

    def test_verify_save_bytes_rejects_bad_magic(self):
        """Bytes with invalid magic header are rejected."""
        corrupted = b"NOPE" + self.canonical_bytes[4:]
        with self.assertRaises(SaveValidationError):
            verify_save_bytes(corrupted)

    def test_verify_save_bytes_rejects_bad_outer_crc(self):
        """Corrupted outer container CRC is rejected when strict_crc=True."""
        corrupted = bytearray(self.canonical_bytes)
        corrupted[4] ^= 0xFF  # Corrupt CRC byte
        with self.assertRaises(SaveValidationError):
            verify_save_bytes(bytes(corrupted), strict_crc=True)

    def test_atomic_write_happy_path(self):
        """Atomic write modifies target, creates backup, and updates file on disk."""
        editor = SaveEditor(self.canonical_bytes)
        editor.set_money(8888888)
        new_bytes = editor.save_to_bytes()

        result = atomic_write_save(
            target_path=self.target_save,
            candidate_bytes=new_bytes,
            expected_baseline_sha256=self.canonical_sha,
            create_backup=True,
            strict_verification=True,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sha256"], compute_sha256(new_bytes))
        self.assertTrue(self.target_save.exists())
        self.assertEqual(self.target_save.read_bytes(), new_bytes)

        # Check backup created
        backup_path = Path(result["backup_path"])
        self.assertTrue(backup_path.exists())
        self.assertTrue(backup_path.name.endswith(".zip"))

    def test_atomic_write_detects_external_conflict(self):
        """External modification to target file raises ConcurrencyConflictError and aborts."""
        editor = SaveEditor(self.canonical_bytes)
        editor.set_money(5555555)
        new_bytes = editor.save_to_bytes()

        # Externally mutate target file
        self.target_save.write_bytes(b"DATA" + b"\x00" * 100)

        with self.assertRaises(ConcurrencyConflictError):
            atomic_write_save(
                target_path=self.target_save,
                candidate_bytes=new_bytes,
                expected_baseline_sha256=self.canonical_sha,
            )

        # Confirm target still has the external content (was not overwritten by candidate)
        self.assertEqual(self.target_save.read_bytes(), b"DATA" + b"\x00" * 100)

    def test_atomic_write_rejects_corrupted_candidate_zero_disk_mutation(self):
        """Corrupted candidate bytes are rejected with zero disk mutation."""
        corrupted_candidate = bytearray(self.canonical_bytes)
        corrupted_candidate[4] ^= 0xFF  # Break CRC

        with self.assertRaises(SaveValidationError):
            atomic_write_save(
                target_path=self.target_save,
                candidate_bytes=bytes(corrupted_candidate),
                expected_baseline_sha256=self.canonical_sha,
                strict_verification=True,
            )

        # Target file must be bit-for-bit identical to original
        self.assertEqual(self.target_save.read_bytes(), self.canonical_bytes)

    def test_atomic_restore_backup(self):
        """Atomic restore extracts valid save from backup ZIP and replaces target."""
        # 1. Modify save and create backup
        editor = SaveEditor(self.canonical_bytes)
        editor.set_money(9999999)
        mod_bytes = editor.save_to_bytes()
        write_res = atomic_write_save(
            target_path=self.target_save,
            candidate_bytes=mod_bytes,
            expected_baseline_sha256=self.canonical_sha,
            create_backup=True,
        )
        backup_zip = Path(write_res["backup_path"])

        # 2. Mutate target again
        editor2 = SaveEditor(mod_bytes)
        editor2.set_money(1111111)
        mod2_bytes = editor2.save_to_bytes()
        self.target_save.write_bytes(mod2_bytes)
        mod2_sha = compute_sha256(mod2_bytes)

        # 3. Restore from first backup
        restore_res = atomic_restore_backup(
            target_path=self.target_save,
            backup_zip=backup_zip,
            expected_baseline_sha256=mod2_sha,
        )

        self.assertEqual(restore_res["status"], "success")
        self.assertEqual(self.target_save.read_bytes(), self.canonical_bytes)


if __name__ == "__main__":
    unittest.main()
