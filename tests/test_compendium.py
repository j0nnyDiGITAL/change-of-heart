"""Regression tests for the compendium registration bitmask (2026-08-14).

Verified layout: 232-bit LSB-first mask @ 0x09973 (mirror 0x21E83),
bit i = persona ID (i+1). Structural + ladder evidence from 7 saves.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.editor import SaveEditor

ORACLE = r"C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT"
FRESH = r"C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT"
ORACLE_AVAILABLE = os.path.isfile(ORACLE) and os.path.isfile(FRESH)


def make_pc_editor() -> SaveEditor:
    e = SaveEditor()
    e.parser.is_pc_0x31 = True
    e.parser.data_payload = bytes(0x40000)
    return e


class TestCompendiumMask(unittest.TestCase):
    def test_get_empty_on_fresh_zeroed(self):
        e = make_pc_editor()
        c = e.get_compendium()
        self.assertTrue(c["supported"])
        self.assertEqual(c["count"], 0)

    def test_set_one_bit_roundtrip(self):
        e = make_pc_editor()
        r = e.set_compendium_registration(0x035, True)
        self.assertEqual(r["status"], "success")
        c = e.get_compendium()
        self.assertIn(0x035, c["registered"])
        self.assertEqual(c["count"], 1)
        # mirror must match
        d = e.parser.data_payload
        idx = 0x035 - 1
        self.assertEqual(d[0x09973 + idx // 8] & (1 << (idx % 8)), 1 << (idx % 8))
        self.assertEqual(d[0x21E83 + idx // 8] & (1 << (idx % 8)), 1 << (idx % 8))

    def test_clear_bit(self):
        e = make_pc_editor()
        e.set_compendium_registration(0x035, True)
        e.set_compendium_registration(0x035, False)
        self.assertEqual(e.get_compendium()["count"], 0)

    def test_out_of_range_rejected(self):
        e = make_pc_editor()
        self.assertEqual(e.set_compendium_registration(0x200, True)["status"], "unsupported")
        self.assertEqual(e.set_compendium_registration(0, True)["status"], "unsupported")

    def test_full_unlock_writes_all_bits(self):
        e = make_pc_editor()
        r = e.unlock_compendium_100()
        self.assertEqual(r["status"], "success")
        self.assertEqual(e.get_compendium()["count"], 232)

    def test_unlock_survives_roundtrip(self):
        e = make_pc_editor()
        e.unlock_compendium_100()
        packed = e.save_to_bytes()
        e2 = SaveEditor(packed)
        self.assertTrue(e2.integrity_report()["ok"])
        self.assertEqual(e2.get_compendium()["count"], 232)


@unittest.skipUnless(ORACLE_AVAILABLE, "oracle saves not on disk")
class TestCompendiumOracle(unittest.TestCase):
    def test_oracle_ladder_counts(self):
        """Known counts: fresh=33, oracle=217 — from the verified ladder."""
        f = SaveEditor(open(FRESH, "rb").read())
        o = SaveEditor(open(ORACLE, "rb").read())
        self.assertTrue(f.get_compendium()["supported"])
        self.assertEqual(f.get_compendium()["count"], 33)
        self.assertEqual(o.get_compendium()["count"], 217)

    def test_fresh_mask_subset_of_oracle(self):
        f = set(SaveEditor(open(FRESH, "rb").read()).get_compendium()["registered"])
        o = set(SaveEditor(open(ORACLE, "rb").read()).get_compendium()["registered"])
        self.assertTrue(f <= o, "fresh mask must be a subset of oracle mask")

    def test_all_set_bits_valid_persona_ids(self):
        """217/217 set bits map to valid Personas.txt IDs."""
        e = SaveEditor(open(ORACLE, "rb").read())
        table = e._load_table("Personas.txt")
        reg = e.get_compendium()["registered"]
        valid = [pid for pid in reg if pid in table]
        self.assertEqual(len(valid), len(reg))


if __name__ == "__main__":
    unittest.main()
