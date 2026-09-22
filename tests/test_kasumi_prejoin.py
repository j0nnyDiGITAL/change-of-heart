import glob
import os
import struct
import sys
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.editor import SaveEditor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def make_pc_editor():
    e = SaveEditor()
    e.parser.is_pc_0x31 = True
    e.parser.data_payload = bytes(0x40000)
    return e


class TestKasumiPreJoin(unittest.TestCase):
    def test_kasumi_prejoin_not_entered(self):
        """Kasumi's slot is game-written at save creation with base values;
        until her story join it must be hidden AND edit-blocked."""
        e = make_pc_editor()
        off = 0x2C + 9 * 0x2B0
        d = bytearray(e.parser.data_payload)
        struct.pack_into("<H", d, off + 0, 358)
        struct.pack_into("<H", d, off + 4, 159)
        d[off + 0x3C] = 43
        struct.pack_into("<H", d, off + 0x3A, 0xF0)
        e.parser.data_payload = bytes(d)
        self.assertFalse(e.is_member_joined(9))
        stats = e.get_party_stats()
        self.assertEqual(stats[9]["joined"], False)
        self.assertEqual(stats[9]["name"], "???")
        r = e.set_party_stat(9, level=50)
        self.assertEqual(r["status"], "invalid", "pre-join Kasumi edit not refused")

    def test_joined_roster_june_save(self):
        """Live June save must show exactly the 5 joined members."""
        appdata = os.environ.get("APPDATA", "")
        candidates = sorted(glob.glob(os.path.join(
            appdata, "SEGA", "P5R", "Steam", "*", "savedata", "DATA01", "backups"))) if appdata else []
        pth = candidates[0] if candidates else None
        zips = sorted(os.listdir(pth)) if pth and os.path.isdir(pth) else []
        if not zips:
            self.skipTest("no backups on disk")
        with zipfile.ZipFile(os.path.join(pth, zips[0])) as z:
            e = SaveEditor(z.read("DATA.DAT"))
        joined = [p["slot"] for p in e.get_party_stats() if p.get("joined")]
        self.assertEqual(joined, [0, 1, 2, 3, 4], f"unexpected roster {joined}")


if __name__ == "__main__":
    unittest.main()