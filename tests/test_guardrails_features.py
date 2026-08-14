"""Regression tests for the 2026-08-14 feature pass:
calendar-aware guardrails, integrity report, and backup list/restore.
"""

import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.editor import SaveEditor
from core.environment import create_timestamped_backup, list_backups, restore_backup


def make_pc_editor() -> SaveEditor:
    """Synthetic 0x31 PC save with a header quick-info date embedded."""
    e = SaveEditor()
    e.parser.is_pc_0x31 = True
    e.parser.data_payload = bytes(0x40000)
    # Fake container header with a quick-info date line.
    e.container.header_bytes = b"".join(
        chr(b).encode() if 32 <= b < 127 else b"\n" for b in range(0x100)
    )
    return e


def set_header_date(e: SaveEditor, date_line: str):
    """Overwrite the container header text block with a date line."""
    text = f"{date_line}\nPLV:22 K\nPLAY TIME:23h 0m\nDIFFICULTY:Normal"
    e.container.header_bytes = text.encode("ascii") + b"\x00" * 64


class TestGuardrails(unittest.TestCase):
    def setUp(self):
        self.e = make_pc_editor()

    def test_faith_rank6_warns_before_january(self):
        set_header_date(self.e, "6/15(Wed) After School,Shujin Classroom")
        warnings = self.e.confidant_guardrails("Faith", 6)
        self.assertEqual(len(warnings), 1)
        self.assertIn("rank 5", warnings[0])

    def test_faith_rank5_ok_before_january(self):
        set_header_date(self.e, "6/15(Wed) After School,Shujin Classroom")
        self.assertEqual(self.e.confidant_guardrails("Faith", 5), [])

    def test_faith_rank6_ok_in_january(self):
        set_header_date(self.e, "1/5(Mon) After School,Shujin Classroom")
        self.assertEqual(self.e.confidant_guardrails("Faith", 6), [])

    def test_councillor_low_rank_warns_after_deadline(self):
        set_header_date(self.e, "11/19(Fri) Evening,Leblanc")
        warnings = self.e.confidant_guardrails("Councillor", 3)
        self.assertEqual(len(warnings), 1)
        self.assertIn("Nov 18", warnings[0])

    def test_councillor_ok_before_deadline(self):
        set_header_date(self.e, "6/15(Wed) After School,Shujin Classroom")
        self.assertEqual(self.e.confidant_guardrails("Councillor", 3), [])

    def test_rank_zero_never_warns(self):
        set_header_date(self.e, "11/19(Fri) Evening,Leblanc")
        self.assertEqual(self.e.confidant_guardrails("Councillor", 0), [])
        self.assertEqual(self.e.confidant_guardrails("Faith", 0), [])

    def test_unknown_confidant_never_warns(self):
        set_header_date(self.e, "6/15(Wed) After School,Shujin Classroom")
        self.assertEqual(self.e.confidant_guardrails("Lovers", 10), [])


class TestIntegrityReport(unittest.TestCase):
    def test_unloaded_editor_reports_not_ok(self):
        e = SaveEditor()
        rep = e.integrity_report()
        self.assertFalse(rep["ok"])

    def test_roundtrip_save_reports_ok(self):
        """A pack->unpack cycle must come back with all layers verified."""
        e = make_pc_editor()
        e.parser.data_payload = bytes(0x40000)
        packed = e.save_to_bytes()
        e2 = SaveEditor(packed)
        rep = e2.integrity_report()
        self.assertTrue(rep["file_crc_ok"], rep)
        self.assertTrue(rep["data_crc_ok"], rep)
        self.assertTrue(rep["aes_ok"], rep)
        self.assertTrue(rep["ok"], rep)


class TestBackupRestore(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="p5r_backup_test_"))
        self.save = self.tmp / "DATA01" / "DATA.DAT"
        self.save.parent.mkdir(parents=True)
        self.save.write_bytes(b"ORIGINAL-BYTES")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_list_backups_newest_first(self):
        b1 = create_timestamped_backup(self.save)
        b2 = create_timestamped_backup(self.save)
        listed = list_backups(self.save)
        self.assertEqual(len(listed), 2)
        # Same-second collision gets a _1 suffix; newest = the suffixed one.
        self.assertEqual(listed[0].name, b2.name)

    def test_restore_roundtrip(self):
        backup = create_timestamped_backup(self.save)
        self.save.write_bytes(b"MODIFIED-BYTES")
        safety = restore_backup(self.save, backup)
        self.assertEqual(self.save.read_bytes(), b"ORIGINAL-BYTES")
        # Pre-restore state preserved for reversibility.
        self.assertTrue(safety.exists())
        with zipfile.ZipFile(safety) as zf:
            self.assertEqual(zf.read("DATA.DAT"), b"MODIFIED-BYTES")

    def test_restore_rejects_wrong_archive(self):
        other = self.tmp / "other.zip"
        with zipfile.ZipFile(other, "w") as zf:
            zf.writestr("SYSTEM.DAT", b"x")
        with self.assertRaises(ValueError):
            restore_backup(self.save, other)

    def test_restore_missing_archive(self):
        with self.assertRaises(FileNotFoundError):
            restore_backup(self.save, self.tmp / "nope.zip")


if __name__ == "__main__":
    unittest.main()
